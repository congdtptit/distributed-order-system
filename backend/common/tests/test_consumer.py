"""The shared consumer against the real Kafka cluster (tier 3): the five steps of section 13.3
and the table "Handling bad messages and unknown events" in section 9 of
docs/01-business-spec.md.

The handler stands in for Inventory's: it writes one outbox row per order, which is the effect
counted. Inventory's own handler arrives in step 2 and gets the same checks there.
"""

import json
import logging
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, LiteralString

import psycopg
import pytest
from confluent_kafka import KafkaError, KafkaException

from common.clock import SystemClock
from common.consumer import ConsumerSettings, Handler, Incoming, MessageConsumer, Outcome
from common.envelope import Envelope, decode, encode, new_envelope
from common.kafka import (
    Outgoing,
    Receiver,
    Record,
    Sender,
    committed_offset,
    end_offset,
)
from common.outbox import enqueue

pytestmark = pytest.mark.tier3

CRASH_SCRIPT = Path(__file__).with_name("crash_consumer.py")
CRASH_EXIT_CODE = 17
CLOCK = SystemClock()


# ---------- helpers ----------


def reserve(conn: psycopg.Connection[Any], message: Incoming) -> None:
    """Same as crash_consumer.reserve: one outbox row per order."""
    env = message.envelope
    reply = new_envelope(
        "OrderReserved",
        order_id=env.order_id,
        branch_id="POS01",
        clock=CLOCK,
        causation_id=env.event_id,
    )
    enqueue(conn, "status-events.POS01", reply)


def order_created(order_id: uuid.UUID | None = None) -> Envelope:
    return new_envelope(
        "OrderCreated",
        order_id=order_id or uuid.uuid4(),
        branch_id="POS01",
        clock=CLOCK,
        payload={
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "name": "Phở bò", "quantity": 1}],
        },
    )


def send(bootstrap: str, topic: str, messages: list[tuple[bytes | None, bytes | None]]) -> None:
    acked = Sender(bootstrap, "test-producer").send_all(
        [Outgoing(topic=topic, key=k, value=v) for k, v in messages]
    )
    assert all(acked)


def send_envelopes(bootstrap: str, topic: str, envelopes: list[Envelope]) -> None:
    send(bootstrap, topic, [(str(e.order_id).encode(), encode(e)) for e in envelopes])


def make_consumer(
    bootstrap: str,
    topic: str,
    dsn: str,
    dlq: str,
    handlers: Mapping[str, Handler],
    *,
    group: str | None = None,
    deciding: bool = True,
    max_attempts: int = 5,
) -> MessageConsumer:
    settings = ConsumerSettings(
        name="inventory-test",
        handlers=handlers,
        deciding=deciding,
        max_attempts=max_attempts,
        dlq_topic=dlq,
        backoff_s=0.01,
        max_backoff_s=0.05,
    )
    return MessageConsumer(
        settings,
        Receiver(bootstrap, group or f"g-{uuid.uuid4().hex[:8]}", [topic], "test-consumer"),
        Sender(bootstrap, "test-dlq"),
        lambda: psycopg.connect(dsn),
    )


def drive(consumer: MessageConsumer, n: int, timeout_s: float = 60) -> list[tuple[Record, Outcome]]:
    """Poll until ``n`` messages have been processed."""
    results: list[tuple[Record, Outcome]] = []
    deadline = time.monotonic() + timeout_s
    while len(results) < n:
        assert time.monotonic() < deadline, f"only {len(results)} of {n} messages arrived"
        result = consumer.poll_once(0.5)
        if result is not None:
            results.append(result)
    return results


def read_all(bootstrap: str, topic: str, n: int, timeout_s: float = 60) -> list[Record]:
    receiver = Receiver(bootstrap, f"reader-{uuid.uuid4().hex[:8]}", [topic], "test-reader")
    records: list[Record] = []
    deadline = time.monotonic() + timeout_s
    try:
        while len(records) < n:
            assert time.monotonic() < deadline, f"only {len(records)} of {n} messages in {topic}"
            record = receiver.poll(0.5)
            if record is not None:
                records.append(record)
    finally:
        receiver.close()
    return records


def rows(dsn: str, query: LiteralString) -> list[tuple[Any, ...]]:
    with psycopg.connect(dsn) as conn:
        return conn.execute(query).fetchall()


def processed(dsn: str) -> set[uuid.UUID]:
    return {r[0] for r in rows(dsn, "SELECT event_id FROM processed_events")}


def outbox_causes(dsn: str) -> list[str]:
    return [r[0] for r in rows(dsn, "SELECT payload->>'causation_id' FROM outbox_events")]


# ---------- scenario 26 ----------


@pytest.mark.kb(26)
def test_process_stopped_between_db_commit_and_offset_commit_has_no_second_effect(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Scenario 26: the consumer process is stopped after the DB commit but before the offset
    commit. Kafka redelivers the message (same ``event_id``); processed_events blocks the
    duplicate and there is no second effect. A new ``event_id`` for the same order is a state
    table matter (BR12) and is tested with each service's handler from step 2."""
    dsn = migrated("inventory-service")
    topic, dlq = new_topic(1), new_topic(1)
    group = f"g-{uuid.uuid4().hex[:8]}"
    message = order_created()
    send_envelopes(kafka_bootstrap, topic, [message])

    crashed = subprocess.run(
        [sys.executable, str(CRASH_SCRIPT), kafka_bootstrap, topic, group, dsn, dlq],
        timeout=90,
        capture_output=True,
        text=True,
    )
    assert crashed.returncode == CRASH_EXIT_CODE, crashed.stderr[-2000:]
    # The DB commit happened, the offset commit did not.
    assert processed(dsn) == {message.event_id}
    assert outbox_causes(dsn) == [str(message.event_id)]
    assert committed_offset(kafka_bootstrap, group, topic, 0) is None

    calls: list[uuid.UUID] = []

    def counting_reserve(conn: psycopg.Connection[Any], incoming: Incoming) -> None:
        calls.append(incoming.envelope.event_id)
        reserve(conn, incoming)

    consumer = make_consumer(
        kafka_bootstrap, topic, dsn, dlq, {"OrderCreated": counting_reserve}, group=group
    )
    try:
        [(record, outcome)] = drive(consumer, 1)
    finally:
        consumer.close()

    # Kafka redelivers the same message.
    assert record.offset == 0
    assert decode(record.value).event_id == message.event_id
    # processed_events blocks the duplicate ...
    assert outcome is Outcome.DUPLICATE
    assert calls == []
    # ... and there is no second effect.
    assert processed(dsn) == {message.event_id}
    assert outbox_causes(dsn) == [str(message.event_id)]
    # The offset is committed this time.
    assert committed_offset(kafka_bootstrap, group, topic, 0) == 1


# ---------- scenario 29 ----------


@pytest.mark.kb(29)
@pytest.mark.parametrize(
    "change",
    [{"event_type": "OrderTeleported"}, {"schema_version": 2}],
    ids=["unknown-event-type", "higher-schema-version"],
)
def test_unknown_event_goes_to_dlq_marks_the_order_and_other_orders_continue(
    migrated: Callable[[str], str],
    new_topic: Callable[[int], str],
    kafka_bootstrap: str,
    change: dict[str, object],
) -> None:
    """Scenario 29: Inventory receives a message with an unknown event_type. The message goes
    to dlq, the order is marked as needing review, and other orders are still processed.
    Section 9 treats a higher schema_version the same way."""
    dsn = migrated("inventory-service")
    topic, dlq = new_topic(1), new_topic(1)  # one partition: the bad message sits in between
    before, after = order_created(), order_created()
    bad = order_created()
    bad_value = json.dumps(bad.to_dict() | change).encode()
    send(
        kafka_bootstrap,
        topic,
        [
            (str(before.order_id).encode(), encode(before)),
            (str(bad.order_id).encode(), bad_value),
            (str(after.order_id).encode(), encode(after)),
        ],
    )

    group = f"g-{uuid.uuid4().hex[:8]}"
    consumer = make_consumer(
        kafka_bootstrap, topic, dsn, dlq, {"OrderCreated": reserve}, group=group
    )
    try:
        results = drive(consumer, 3)
        assert [o for _, o in results] == [
            Outcome.HANDLED,
            Outcome.DEAD_LETTERED,
            Outcome.HANDLED,
        ]

        # The message goes to dlq, unchanged, with headers naming where it came from.
        [dead] = read_all(kafka_bootstrap, dlq, 1)
        assert dead.value == bad_value
        assert dead.key == str(bad.order_id).encode()
        headers = dict(dead.headers)
        assert headers["original_topic"] == topic.encode()
        assert headers["original_partition"] == b"0"
        assert headers["original_offset"] == b"1"
        assert headers["consumer"] == b"inventory-test"
        assert headers["error"]

        # The order is marked as needing review.
        alert_query = (
            "SELECT kind, order_id, event_id, source_topic, source_partition, source_offset"
            " FROM alerts"
        )
        assert rows(dsn, alert_query) == [("CAN_KIEM_TRA", bad.order_id, bad.event_id, topic, 0, 1)]
        # It was not processed: no dedup row, no outgoing message.
        assert bad.event_id not in processed(dsn)

        # Other orders are still processed.
        assert processed(dsn) == {before.event_id, after.event_id}
        assert sorted(outbox_causes(dsn)) == sorted([str(before.event_id), str(after.event_id)])
        assert committed_offset(kafka_bootstrap, group, topic, 0) == 3

        # A redelivery of the bad message does not mark the order a second time.
        bad_record = results[1][0]
        assert consumer.process(bad_record) is Outcome.DEAD_LETTERED
        assert len(rows(dsn, "SELECT 1 FROM alerts")) == 1
    finally:
        consumer.close()


# ---------- the rest of the table in section 9 ----------


def test_unreadable_message_is_tried_n_times_then_goes_to_dlq(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    dsn = migrated("kitchen-service")
    topic, dlq = new_topic(1), new_topic(1)
    order_id = uuid.uuid4()
    garbage = b"\x00 not an envelope"
    after = order_created()
    send(
        kafka_bootstrap,
        topic,
        [(str(order_id).encode(), garbage), (str(after.order_id).encode(), encode(after))],
    )
    consumer = make_consumer(
        kafka_bootstrap, topic, dsn, dlq, {"OrderCreated": reserve}, max_attempts=3
    )
    try:
        assert [o for _, o in drive(consumer, 2)] == [Outcome.DEAD_LETTERED, Outcome.HANDLED]
    finally:
        consumer.close()
    [dead] = read_all(kafka_bootstrap, dlq, 1)
    assert dead.value == garbage
    assert b"UnreadableMessage" in dict(dead.headers)["error"]
    # The order ID comes from the Kafka key; there is no readable event_id.
    assert rows(dsn, "SELECT kind, order_id, event_id FROM alerts") == [
        ("CAN_KIEM_TRA", order_id, None)
    ]
    assert processed(dsn) == {after.event_id}


def test_a_handler_that_keeps_failing_is_rolled_back_and_dead_lettered_after_n_attempts(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    dsn = migrated("inventory-service")
    topic, dlq = new_topic(1), new_topic(1)
    message = order_created()
    send_envelopes(kafka_bootstrap, topic, [message])
    attempts: list[int] = []

    def broken(conn: psycopg.Connection[Any], incoming: Incoming) -> None:
        reserve(conn, incoming)  # written, then rolled back with the dedup row
        attempts.append(1)
        raise RuntimeError("bug in the handler")

    consumer = make_consumer(kafka_bootstrap, topic, dsn, dlq, {"OrderCreated": broken})
    try:
        assert [o for _, o in drive(consumer, 1)] == [Outcome.DEAD_LETTERED]
    finally:
        consumer.close()
    assert len(attempts) == 5  # section 10 of the specification
    assert processed(dsn) == set()
    assert outbox_causes(dsn) == []
    [dead] = read_all(kafka_bootstrap, dlq, 1)
    assert b"bug in the handler" in dict(dead.headers)["error"]
    assert rows(dsn, "SELECT order_id, event_id FROM alerts") == [
        (message.order_id, message.event_id)
    ]


def test_a_known_type_meant_for_another_service_is_skipped_without_dlq(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Section 2 of docs/02-detailed-design.md: no processed_events row, no dlq."""
    dsn = migrated("kitchen-service")
    topic, dlq = new_topic(1), new_topic(1)
    heartbeat = new_envelope(
        "Heartbeat", order_id=None, branch_id=None, clock=CLOCK, payload={"epoch": 1, "seq": 7}
    )
    send(kafka_bootstrap, topic, [(b"heartbeat", encode(heartbeat))])
    consumer = make_consumer(kafka_bootstrap, topic, dsn, dlq, {"OrderReserved": reserve})
    try:
        assert [o for _, o in drive(consumer, 1)] == [Outcome.SKIPPED]
    finally:
        consumer.close()
    assert processed(dsn) == set()
    assert rows(dsn, "SELECT 1 FROM alerts") == []
    assert end_offset(kafka_bootstrap, dlq, 0) == 0


def test_display_only_side_alerts_and_skips_an_unknown_type(
    migrated: Callable[[str], str],
    new_topic: Callable[[int], str],
    kafka_bootstrap: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Section 9: a branch logs, raises an alert and ignores an unknown type; no dlq. The alert
    is a row in the branch's own ``alerts`` table (revision 14 of document 02)."""
    dsn = migrated("order-service")
    topic, dlq = new_topic(1), new_topic(1)
    unknown = order_created()
    send(
        kafka_bootstrap,
        topic,
        [
            (
                str(unknown.order_id).encode(),
                json.dumps(unknown.to_dict() | {"event_type": "X"}).encode(),
            )
        ],
    )
    consumer = make_consumer(kafka_bootstrap, topic, dsn, dlq, {}, deciding=False)
    with caplog.at_level(logging.ERROR, logger="common.consumer"):
        try:
            assert [o for _, o in drive(consumer, 1)] == [Outcome.IGNORED_UNKNOWN]
        finally:
            consumer.close()
    assert any(
        "ALERT CAN_KIEM_TRA" in r.message and str(unknown.order_id) in r.message
        for r in caplog.records
    )
    assert rows(dsn, "SELECT kind, order_id, event_id, source_topic FROM alerts") == [
        ("CAN_KIEM_TRA", unknown.order_id, unknown.event_id, topic)
    ]
    assert end_offset(kafka_bootstrap, dlq, 0) == 0
    assert processed(dsn) == set()


def test_a_message_interrupted_by_a_kafka_error_is_read_again_not_passed_over(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Section 9: a message is never ignored silently. If its five steps stop on a Kafka
    error, the consumer reads it again; step 2 blocks the repeat if its DB commit happened."""
    dsn = migrated("inventory-service")
    topic, dlq = new_topic(1), new_topic(1)
    first, second = order_created(), order_created()
    send_envelopes(kafka_bootstrap, topic, [first, second])
    consumer = make_consumer(kafka_bootstrap, topic, dsn, dlq, {"OrderCreated": reserve})
    receiver = consumer._receiver  # pyright: ignore[reportPrivateUsage]
    real_commit = receiver.commit
    failures = [KafkaException(KafkaError(KafkaError._TRANSPORT))]  # pyright: ignore[reportPrivateUsage]

    def commit_fails_once(record: Record) -> None:  # step 5 fails after the DB commit
        if failures:
            raise failures.pop()
        real_commit(record)

    receiver.commit = commit_fails_once
    try:
        with pytest.raises(KafkaException):
            while consumer.poll_once(0.5) is None:
                pass
        results = drive(consumer, 2)
    finally:
        consumer.close()
    assert [(r.offset, o) for r, o in results] == [(0, Outcome.DUPLICATE), (1, Outcome.HANDLED)]
    assert processed(dsn) == {first.event_id, second.event_id}
    assert sorted(outbox_causes(dsn)) == sorted([str(first.event_id), str(second.event_id)])
