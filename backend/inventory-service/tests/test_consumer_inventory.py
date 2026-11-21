"""Scenarios 26 and 29 with Inventory's real handlers (tier 3, real brokers).

Step 1 proved the shared consumer with a stand-in handler (common/tests/test_consumer.py);
these versions count Inventory's real effects: the order record, the stock, the outbox rows,
and the invariants. Throwaway ``test.*`` topics stand in for ``order-events.POS01``.
"""

import json
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from inventory_support import (
    D,
    alerts,
    assert_invariants,
    handlers,
    order_created,
    order_record,
    outbox,
    processed,
    reservations,
    seeded,
    stock,
)

from common.clock import SystemClock
from common.consumer import ConsumerSettings, MessageConsumer, Outcome
from common.envelope import Envelope, encode
from common.kafka import Outgoing, Receiver, Record, Sender, committed_offset
from inventory_service.orders import Limits

pytestmark = pytest.mark.tier3

CRASH_SCRIPT = Path(__file__).with_name("crash_inventory.py")
PHO_BO = {"BANH_PHO": D("0.2"), "THIT_BO": D("0.15"), "RAU_SONG": D("0.05")}


def now_order() -> Envelope:
    return order_created(created_at=datetime.now(UTC))


def consumer(bootstrap: str, topic: str, dsn: str, dlq: str, group: str) -> MessageConsumer:
    return MessageConsumer(
        ConsumerSettings(
            name="inventory-test",
            handlers=handlers(SystemClock(), Limits()),
            deciding=True,
            dlq_topic=dlq,
            backoff_s=0.01,
            max_backoff_s=0.05,
        ),
        Receiver(bootstrap, group, [topic], "inventory-test"),
        Sender(bootstrap, "inventory-test"),
        lambda: psycopg.connect(dsn),
        branch_of=lambda _topic: "POS01",
    )


def drive(c: MessageConsumer, n: int) -> list[tuple[Record, Outcome]]:
    results: list[tuple[Record, Outcome]] = []
    deadline = time.monotonic() + 60
    while len(results) < n:
        assert time.monotonic() < deadline, f"only {len(results)} of {n} messages arrived"
        if (r := c.poll_once(0.5)) is not None:
            results.append(r)
    return results


def send(bootstrap: str, topic: str, messages: list[tuple[uuid.UUID | None, bytes]]) -> None:
    acked = Sender(bootstrap, "test-pos01").send_all(
        [Outgoing(topic, str(k).encode(), v) for k, v in messages]
    )
    assert all(acked)


@pytest.mark.kb(26)
def test_inventory_stopped_between_db_commit_and_offset_commit_reserves_once(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Scenario 26 with Inventory: the consumer process is stopped after the DB commit but
    before the offset commit. Kafka redelivers the message; processed_events blocks the
    duplicate and there is no second effect: one record, stock deducted once, one pair of
    outgoing messages."""
    dsn = seeded(migrated("inventory-service"))
    topic, dlq = new_topic(1), new_topic(1)
    group = f"g-{uuid.uuid4().hex[:8]}"
    before = stock(dsn)
    order = now_order()
    send(kafka_bootstrap, topic, [(order.order_id, encode(order))])

    crashed = subprocess.run(
        [sys.executable, str(CRASH_SCRIPT), kafka_bootstrap, topic, group, dsn, dlq],
        timeout=90,
        capture_output=True,
        text=True,
    )
    assert crashed.returncode == 17, crashed.stderr[-2000:]
    effect = (stock(dsn), outbox(dsn), reservations(dsn, order.order_id))
    assert effect[2] == PHO_BO
    assert [(r.topic, r.event_type) for r in effect[1]] == [
        ("kitchen-orders", "OrderReserved"),
        ("status-events.POS01", "OrderReserved"),
    ]
    assert committed_offset(kafka_bootstrap, group, topic, 0) is None

    c = consumer(kafka_bootstrap, topic, dsn, dlq, group)
    try:
        [(record, outcome)] = drive(c, 1)
    finally:
        c.close()
    assert record.offset == 0  # Kafka redelivers ...
    assert outcome is Outcome.DUPLICATE  # ... processed_events blocks the duplicate ...
    assert (
        stock(dsn),
        outbox(dsn),
        reservations(dsn, order.order_id),
    ) == effect  # ... no second effect
    for ingredient, q in PHO_BO.items():
        assert effect[0][ingredient].available == before[ingredient].available - q
    assert processed(dsn) == {order.event_id}
    assert committed_offset(kafka_bootstrap, group, topic, 0) == 1
    assert_invariants(dsn)


@pytest.mark.kb(29)
def test_inventory_moves_an_unknown_event_to_dlq_and_keeps_reserving_other_orders(
    migrated: Callable[[str], str], new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    """Scenario 29 with Inventory: Inventory receives a message with an unknown event_type.
    The message goes to dlq, the order is marked as needing review, and other orders are still
    processed (reserved, with their messages to the Kitchen and the branch)."""
    dsn = seeded(migrated("inventory-service"))
    topic, dlq = new_topic(1), new_topic(1)
    first, bad, last = now_order(), now_order(), now_order()
    bad_value = json.dumps(bad.to_dict() | {"event_type": "OrderTeleported"}).encode()
    send(
        kafka_bootstrap,
        topic,
        [(first.order_id, encode(first)), (bad.order_id, bad_value), (last.order_id, encode(last))],
    )
    c = consumer(kafka_bootstrap, topic, dsn, dlq, f"g-{uuid.uuid4().hex[:8]}")
    try:
        outcomes = [o for _, o in drive(c, 3)]
    finally:
        c.close()
    assert outcomes == [Outcome.HANDLED, Outcome.DEAD_LETTERED, Outcome.HANDLED]

    # The message goes to dlq.
    reader = Receiver(kafka_bootstrap, f"r-{uuid.uuid4().hex[:8]}", [dlq], "reader")
    try:
        dead = None
        deadline = time.monotonic() + 30
        while dead is None and time.monotonic() < deadline:
            dead = reader.poll(0.5)
    finally:
        reader.close()
    assert dead is not None and dead.value == bad_value
    # The order is marked as needing review; it has no record and reserved nothing.
    assert alerts(dsn) == [("CAN_KIEM_TRA", bad.order_id, bad.event_id)]
    assert order_record(dsn, bad.order_id) is None
    # Other orders are still processed.
    for order in (first, last):
        record = order_record(dsn, order.order_id)
        assert record is not None and record[0] == "DANG_GIU"
        assert reservations(dsn, order.order_id) == PHO_BO
    replies = {(r.topic, r.causation_id) for r in outbox(dsn)}
    for order in (first, last):
        assert ("kitchen-orders", str(order.event_id)) in replies
        assert ("status-events.POS01", str(order.event_id)) in replies
    assert_invariants(dsn)
