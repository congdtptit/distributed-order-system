"""Scenario 25 end to end (tier 3) on the running cluster: the Kitchen is stopped while orders
and cancel requests keep coming, then started again."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any, LiteralString, Protocol

import inventory_support as inv
import psycopg
import pytest
from kitchen_support import cancel_requested

from common.envelope import Envelope, decode, encode
from common.kafka import Outgoing, Record, Sender, TopicTail
from inventory_service.invariants import violations
from inventory_service.stock import receive_stock

pytestmark = pytest.mark.tier3

INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
KITCHEN_DB = "postgresql://app:app@kitchen-db:5432/kitchen"
ORDERS = 10


class Chaos(Protocol):
    def stop(self, service: str) -> None: ...
    def start(self, service: str) -> None: ...
    def wait_healthy(self, service: str, timeout_s: float = 120) -> None: ...
    def health(self, service: str) -> str: ...


QUERIES: dict[str, LiteralString] = {
    "inventory_orders": "SELECT order_id, status FROM inventory_orders WHERE order_id = ANY(%s)",
    "kitchen_orders": "SELECT order_id, status FROM kitchen_orders WHERE order_id = ANY(%s)",
}


def statuses(dsn: str, table: str, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    with psycopg.connect(dsn) as conn:
        return {r[0]: str(r[1]) for r in conn.execute(QUERIES[table], (ids,)).fetchall()}


def wait_until(what: str, timeout_s: float, check: Any) -> None:
    deadline = time.monotonic() + timeout_s
    while not check():
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.5)


@pytest.mark.kb(25)
def test_the_kitchen_down_while_messages_arrive_processes_all_of_them_once(
    kafka_bootstrap: str, chaos: Chaos
) -> None:
    """Scenario 25: the Kitchen is shut down for 2 hours while orders and cancel requests keep
    coming, then started again. The Kitchen processes every message still in Kafka, with none
    lost and none duplicated.

    The test keeps the Kitchen down for the time it takes to send the messages (seconds, not
    2 hours): Kafka keeps messages for 7 days (section 13.1), so the length of the outage does
    not change what the Kitchen finds when it returns. Half the orders get a cancel request,
    some sent before their order and some after."""
    with psycopg.connect(INVENTORY_DB) as conn:
        for ingredient in ("LA_TRA", "DA"):
            assert receive_stock(conn, ingredient, inv.D("5"))
    orders: list[Envelope] = [
        inv.order_created(created_at=datetime.now(UTC), items=[("TRA_DA", 1)])
        for _ in range(ORDERS)
    ]
    ids = [o.order_id for o in orders if o.order_id is not None]
    cancelled = set(ids[: ORDERS // 2])
    sender = Sender(kafka_bootstrap, "test-pos01")

    def send(topic: str, env: Envelope) -> None:
        assert sender.send_all([Outgoing(topic, str(env.order_id).encode(), encode(env))]) == [True]

    tail = TopicTail(kafka_bootstrap, ["status-events.POS01", "stock-commands"])
    chaos.stop("kitchen")
    try:
        for i, order in enumerate(orders):
            cancel = cancel_requested(order.order_id) if order.order_id in cancelled else None
            if cancel is not None and i % 2 == 0:
                send("cancel-events.POS01", cancel)  # before its order
            send("order-events.POS01", order)
            if cancel is not None and i % 2 == 1:
                send("cancel-events.POS01", cancel)  # after its order
        # Inventory keeps working: every order is reserved and forwarded while the Kitchen is down.
        wait_until(
            "Inventory to reserve",
            60,
            lambda: (
                statuses(INVENTORY_DB, "inventory_orders", ids) == dict.fromkeys(ids, "DANG_GIU")
            ),
        )
        assert chaos.health("kitchen") != "healthy"
        assert statuses(KITCHEN_DB, "kitchen_orders", ids) == {}

        chaos.start("kitchen")
        chaos.wait_healthy("kitchen")
        expected = {i: ("DA_HUY" if i in cancelled else "CHO_NAU") for i in ids}
        # Every message is processed: each order ends where table 3.2 puts it.
        wait_until(
            "the Kitchen to catch up",
            90,
            lambda: statuses(KITCHEN_DB, "kitchen_orders", ids) == expected,
        )
        wait_until(
            "Inventory to release the cancelled orders",
            60,
            lambda: (
                {
                    i
                    for i, s in statuses(INVENTORY_DB, "inventory_orders", ids).items()
                    if s == "DA_TRA"
                }
                == cancelled
            ),
        )
        seen: list[Record] = tail.read(5)
    finally:
        tail.close()

    # None duplicated: one Cancelled to the branch and one release command per cancelled order,
    # nothing of the kind for the others.
    ours = [r for r in seen if r.key is not None and uuid.UUID(r.key.decode()) in set(ids)]
    by_type: dict[str, list[uuid.UUID]] = {}
    for r in ours:
        env = decode(r.value)
        assert env.order_id is not None
        by_type.setdefault(env.event_type, []).append(env.order_id)
    assert sorted(by_type.get("OrderCancelled", [])) == sorted(cancelled)
    assert sorted(by_type.get("ReleaseRequested", [])) == sorted(cancelled)
    pending = by_type.get("CancelPending", [])
    assert len(pending) == len(set(pending)) and set(pending) <= cancelled
    with psycopg.connect(INVENTORY_DB) as conn:
        assert violations(conn) == {}
