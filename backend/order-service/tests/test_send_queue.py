"""The branch's sender and consumer against the real Kafka cluster (tier 3).

The orders are real branch orders; their entries are pointed at throwaway topics (``test.``),
so that Inventory's ``^order-events\\..*`` subscription never sees them.
"""

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Protocol

import psycopg
import pytest
from branch_support import entries, order_row, place, status_message

from common.clock import SystemClock
from common.consumer import ConsumerSettings, MessageConsumer, Outcome
from common.envelope import decode, encode
from common.kafka import (
    Outgoing,
    Receiver,
    Record,
    Sender,
    create_topic,
    delete_topics,
    end_offset,
    partition_leaders,
)
from order_service.orders import Line, cancel_order, create_order
from order_service.sender import SendQueue
from order_service.statuses import branch_handlers

pytestmark = pytest.mark.tier3

CLOCK = SystemClock()


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def kill(self, service: str) -> None: ...
    def health(self, service: str) -> str: ...
    def disconnect(self, service: str, network: str = "kafka-net") -> None: ...
    def connect(self, service: str, network: str = "kafka-net") -> None: ...


def place_on(dsn: str, topic: str) -> uuid.UUID:
    """A real order whose create-order entry goes to ``topic``, in one transaction, so the
    sender never sees it pointed at the real ``order-events.POS01``."""
    with psycopg.connect(dsn) as conn:
        order = create_order(conn, "POS01", [Line("TRA_DA", 1)], CLOCK)
        conn.execute(
            "UPDATE outbox_events SET topic = %s WHERE order_id = %s", (topic, order["order_id"])
        )
        conn.commit()
    return order["order_id"]


def cancel_on(dsn: str, order_id: uuid.UUID, topic: str) -> None:
    """The cashier cancels an attempted order; its cancel entry goes to ``topic``."""
    with psycopg.connect(dsn) as conn:
        assert not cancel_order(conn, "POS01", order_id, "CHANGED_MIND", CLOCK).local
        conn.execute(
            "UPDATE outbox_events SET topic = %s WHERE order_id = %s AND kind = 'HUY'",
            (topic, order_id),
        )
        conn.commit()


def read_topic(bootstrap: str, topic: str, until: Callable[[list[Record]], bool]) -> list[Record]:
    receiver = Receiver(bootstrap, f"reader-{uuid.uuid4().hex[:8]}", [topic], "reader")
    records: list[Record] = []
    deadline = time.monotonic() + 60
    try:
        while not until(records):
            assert time.monotonic() < deadline, f"read {len(records)} records from {topic}"
            record = receiver.poll(0.5)
            if record is not None:
                records.append(record)
    finally:
        receiver.close()
    return records


def wait_for(condition: Callable[[], bool], timeout_s: float, what: str) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.2)


@pytest.mark.kb(12)
def test_attempted_entries_that_keep_failing_are_never_dropped_and_go_in_order(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Scenario 12: entries that have been attempted fail to send many times. No entry is
    discarded; when sending works again every entry is sent, in the right order per order ID.

    The failure is a topic the brokers do not have yet: the probe succeeds (the cluster
    answers), the flag is set, and every send fails until the topic is created, which stands
    for the network coming back. Another order's entry to a working topic is not held up.
    """
    working = new_topic(2)
    missing = f"test.{uuid.uuid4().hex[:12]}"
    queue = SendQueue(
        lambda: psycopg.connect(bdb),
        Sender(kafka_bootstrap, "test-branch-sender", delivery_timeout_s=3),
        CLOCK,
    )
    a, b = place_on(bdb, missing), place_on(bdb, missing)
    other = place_on(bdb, working)
    try:
        first = queue.send_once()
        assert (first.sent, first.failed) == (1, 2)
        assert entries(bdb, other)[0]["sent_at"] is not None  # not held up by a and b
        cancel_on(bdb, a, missing)  # a was attempted: its cancel goes behind it

        failures = first.failed
        for _ in range(3):
            result = queue.send_once()
            assert result.sent == 0
            failures += result.failed
            # Nothing is dropped; the cancel entry is never attempted before a's create-order
            # entry is acknowledged.
            assert [(e["kind"], e["attempted"], e["sent_at"]) for e in entries(bdb, a)] == [
                ("TAO_DON", True, None),
                ("HUY", False, None),
            ]
            assert [(e["attempted"], e["sent_at"]) for e in entries(bdb, b)] == [(True, None)]
        assert failures == 8

        create_topic(kafka_bootstrap, missing, 2)  # sending works again
        deadline = time.monotonic() + 60
        while any(e["sent_at"] is None for e in entries(bdb)):
            assert time.monotonic() < deadline, "the entries were not all sent"
            queue.send_once()

        records = read_topic(kafka_bootstrap, missing, lambda r: len(r) >= 3)
    finally:
        delete_topics(kafka_bootstrap, [missing])

    sent: dict[uuid.UUID, list[tuple[int, int, str]]] = {}
    for r in records:
        env = decode(r.value)
        assert env.order_id is not None
        sent.setdefault(env.order_id, []).append((r.partition, r.offset, env.event_type))
    assert [t for _, _, t in sorted(sent[a])] == ["OrderCreated", "CancelRequested"]
    assert len({p for p, _, _ in sent[a]}) == 1  # one partition: Kafka keeps their order
    assert [t for _, _, t in sent[b]] == ["OrderCreated"]


@pytest.mark.kb(12)
def test_attempted_entries_survive_a_real_network_cut(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str, chaos: Chaos
) -> None:
    """Scenario 12 with the connection really dropped: the test process (the tools container)
    is cut off ``kafka-net`` while entries that carry the flag are being sent, so their outcome
    is unknown, and stays cut for several rounds. Entries placed meanwhile wait unattempted.
    After reconnecting every entry is sent, a cancel entry after its create-order entry; the
    order cancelled locally while cut off is never sent."""
    topic = new_topic(2)
    queue = SendQueue(
        lambda: psycopg.connect(bdb),
        Sender(kafka_bootstrap, "test-cut", delivery_timeout_s=3),
        CLOCK,
        probe_timeout_s=1,
    )
    before = [place_on(bdb, topic) for _ in range(3)]
    assert queue.send_once().sent == 3

    flagged = [place_on(bdb, topic) for _ in range(3)]
    with psycopg.connect(bdb, autocommit=True) as conn:
        ids = [e["id"] for o in flagged for e in entries(bdb, o)]
        assert queue.start_attempts(conn, ids) == set(ids)
    in_flight = threading.Thread(target=queue.send_once)
    in_flight.start()
    time.sleep(0.005)
    chaos.disconnect("tools")  # the network drops while they are being sent
    in_flight.join(60)

    during = [place_on(bdb, topic) for _ in range(2)]
    cancel_on(bdb, flagged[0], topic)  # attempted: the cancel goes behind it
    with psycopg.connect(bdb) as conn:  # never attempted: cancelled here
        assert cancel_order(conn, "POS01", during[0], "CHANGED_MIND", CLOCK).local
        conn.commit()
    for _ in range(3):
        queue.send_once()
        for order_id in flagged:
            if (created := entries(bdb, order_id)[0])["sent_at"] is None:
                assert created["attempted"]  # kept, flag and all
        assert [e["attempted"] for e in entries(bdb, during[1])] == [False]
    assert queue.status.connected is False

    chaos.connect("tools")
    deadline = time.monotonic() + 90
    while any(e["sent_at"] is None for e in entries(bdb)):
        assert time.monotonic() < deadline, "the entries were not all sent after reconnecting"
        queue.send_once()

    expected = {*before, *flagged, during[1]}
    first: dict[tuple[uuid.UUID, str], tuple[int, int]] = {}

    def complete(records: list[Record]) -> bool:
        for r in records:
            env = decode(r.value)
            assert env.order_id is not None
            first.setdefault((env.order_id, env.event_type), (r.partition, r.offset))
        return {o for o, t in first if t == "OrderCreated"} >= expected and (
            (flagged[0], "CancelRequested") in first
        )

    read_topic(kafka_bootstrap, topic, complete)
    assert during[0] not in {o for o, _ in first}
    created, cancel = first[(flagged[0], "OrderCreated")], first[(flagged[0], "CancelRequested")]
    assert created[0] == cancel[0] and created[1] < cancel[1]


def test_a_message_kafka_refuses_does_not_block_the_queue(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Section 9: one failing entry does not block the send queue. An entry the producer refuses
    outright (larger than the 1 MB message limit) fails and stays queued with its flag, as
    section 15 of the specification accepts; the other orders' entries are sent."""
    topic = new_topic(1)
    huge, normal = place_on(bdb, topic), place_on(bdb, topic)
    with psycopg.connect(bdb) as conn:
        conn.execute(
            "UPDATE outbox_events SET payload = payload || jsonb_build_object('pad', repeat('x',"
            " 2000000)) WHERE order_id = %s",
            (huge,),
        )
        conn.commit()
    queue = SendQueue(lambda: psycopg.connect(bdb), Sender(kafka_bootstrap, "test-big"), CLOCK)
    result = queue.send_once()
    assert (result.sent, result.failed) == (1, 1)
    assert [(e["attempted"], e["sent_at"] is None) for e in entries(bdb, huge)] == [(True, True)]
    assert entries(bdb, normal)[0]["sent_at"] is not None


@pytest.mark.kb(10)
def test_unreachable_kafka_sets_no_flag_so_the_order_can_still_be_cancelled_here(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """BR9 and scenario 10 in one process: while the probe fails (a client whose brokers
    cannot be reached), the sender neither sets the flag nor sends; the cashier's cancel is
    local. When Kafka is reachable again (a client of the real cluster), only the order that
    was not cancelled is sent."""
    topic = new_topic(1)
    offline = SendQueue(
        lambda: psycopg.connect(bdb),
        Sender("127.0.0.1:1", "test-offline", delivery_timeout_s=2),
        CLOCK,
        probe_timeout_s=1,
    )
    cancelled, kept = place_on(bdb, topic), place_on(bdb, topic)
    for _ in range(2):
        result = offline.send_once()
        assert (result.sent, result.failed, result.held) == (0, 0, 2)
        assert offline.status.connected is False
    assert [e["attempted"] for e in entries(bdb)] == [False, False]
    with psycopg.connect(bdb) as conn:
        assert cancel_order(conn, "POS01", cancelled, "CHANGED_MIND", CLOCK).local
        conn.commit()

    online = SendQueue(lambda: psycopg.connect(bdb), Sender(kafka_bootstrap, "test-online"), CLOCK)
    assert online.send_once().sent == 1
    assert online.status.connected is True
    records = read_topic(kafka_bootstrap, topic, lambda r: len(r) >= 1)
    assert [decode(r.value).order_id for r in records] == [kept]
    assert entries(bdb, cancelled) == []


@pytest.mark.kb(31)
def test_a_broker_killed_while_the_branch_sends_loses_no_acknowledged_entry(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str, chaos: Chaos
) -> None:
    """Scenario 31 for the branch's send queue: the broker leading a partition is killed
    (SIGKILL) while orders keep arriving and being sent. No entry Kafka acknowledged is lost
    and sending continues."""
    topic = new_topic(2)
    queue = SendQueue(lambda: psycopg.connect(bdb), Sender(kafka_bootstrap, "test-31"), CLOCK)
    stop = threading.Event()
    sender = threading.Thread(target=queue.run, args=(stop,), daemon=True)
    placed: list[uuid.UUID] = []

    def cashier() -> None:
        for _ in range(300):
            placed.append(place_on(bdb, topic))
            time.sleep(0.02)

    writer = threading.Thread(target=cashier, daemon=True)

    def acknowledged() -> list[dict[str, Any]]:
        return [e for e in entries(bdb) if e["sent_at"] is not None]

    sender.start()
    try:
        writer.start()
        wait_for(lambda: len(acknowledged()) >= 50, 60, "50 entries sent")
        leader = partition_leaders(kafka_bootstrap, topic)[0]
        assert writer.is_alive(), "orders stopped arriving before the broker died"
        chaos.kill(f"kafka{leader}")
        last_before_kill = entries(bdb)[-1]["id"]
        writer.join(timeout=60)
        assert not writer.is_alive()

        wait_for(lambda: len(acknowledged()) == len(placed), 120, "every entry sent")
        assert chaos.health(f"kafka{leader}") != "healthy"
        assert len([e for e in entries(bdb) if e["id"] > last_before_kill]) > 100
        assert partition_leaders(kafka_bootstrap, topic)[0] not in (leader, -1)
    finally:
        stop.set()
        sender.join(timeout=60)

    expected = {uuid.UUID(e["payload"]["event_id"]) for e in acknowledged()}
    assert len(expected) == len(placed)
    received: set[uuid.UUID] = set()

    def has_all(records: list[Record]) -> bool:
        received.update(decode(r.value).event_id for r in records[len(received) :])
        return expected <= received

    read_topic(kafka_bootstrap, topic, has_all)


def drive(consumer: MessageConsumer, n: int) -> list[Outcome]:
    outcomes: list[Outcome] = []
    deadline = time.monotonic() + 60
    while len(outcomes) < n:
        assert time.monotonic() < deadline, f"only {len(outcomes)} of {n} messages processed"
        result = consumer.poll_once(0.5)
        if result is not None:
            outcomes.append(result[1])
    return outcomes


def branch_consumer(bootstrap: str, topic: str, dlq: str, dsn: str) -> MessageConsumer:
    return MessageConsumer(
        ConsumerSettings(
            name="branch-test",
            handlers=branch_handlers("POS01"),
            deciding=False,
            dlq_topic=dlq,
            backoff_s=0.01,
            max_backoff_s=0.05,
        ),
        Receiver(bootstrap, f"g-{uuid.uuid4().hex[:8]}", [topic], "branch-test"),
        Sender(bootstrap, "branch-test-dlq"),
        lambda: psycopg.connect(dsn),
        branch_of=lambda _topic: "POS01",  # the throwaway topic stands for status-events.POS01
    )


def test_the_branch_consumer_alerts_on_bad_messages_and_keeps_going(
    bdb: str, new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Section 9, display-only side, with the branch's ``alerts`` table (revision 14 of
    document 02): an unreadable message goes to the dlq with an alert; an unknown type is
    alerted and ignored; the next message is applied; reading it all again adds no alert."""
    topic, dlq = new_topic(1), new_topic(1)
    order_id = place(bdb)
    reserved = status_message("OrderReserved", order_id)
    unknown = replace(reserved, event_id=uuid.uuid4(), event_type="OrderTeleported")
    key = str(order_id).encode()
    assert all(
        Sender(kafka_bootstrap, "test-producer").send_all(
            [
                Outgoing(topic, key, b"not json"),
                Outgoing(topic, key, encode(unknown)),
                Outgoing(topic, key, encode(reserved)),
            ]
        )
    )

    for expected in (
        [Outcome.DEAD_LETTERED, Outcome.IGNORED_UNKNOWN, Outcome.HANDLED],
        [Outcome.DEAD_LETTERED, Outcome.IGNORED_UNKNOWN, Outcome.DUPLICATE],  # read again
    ):
        consumer = branch_consumer(kafka_bootstrap, topic, dlq, bdb)
        try:
            assert drive(consumer, 3) == expected
        finally:
            consumer.close()
        with psycopg.connect(bdb) as conn:
            alerts = conn.execute(
                "SELECT kind, order_id, event_id, source_offset FROM alerts ORDER BY id"
            ).fetchall()
        assert alerts == [
            ("CAN_KIEM_TRA", order_id, None, 0),
            ("CAN_KIEM_TRA", order_id, unknown.event_id, 1),
        ]
        row = order_row(bdb, order_id)
        assert row is not None and row["status"] == "DA_GIU"
    assert end_offset(kafka_bootstrap, dlq, 0) >= 1
