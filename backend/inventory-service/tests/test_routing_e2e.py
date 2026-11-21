"""Scenario 24 end to end (tier 3): the running Inventory service of the compose cluster
consumes ``order-events.POS01`` from the real brokers and its outbox relay writes the results.

Needs the cluster up (``docker compose up -d --wait``): the test talks to the real topics and
to ``inventory-db``, and tops up stock there first so that repeated runs keep passing.
"""

import time
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from inventory_support import D, order_created

from common.envelope import decode, encode
from common.kafka import Outgoing, Record, Sender, TopicTail
from inventory_service.invariants import violations
from inventory_service.stock import receive_stock

pytestmark = pytest.mark.tier3

INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
WATCHED = [
    "kitchen-orders",
    "status-events.POS01",
    "status-events.POS02",
    "status-events.ONLINE",
]


@pytest.mark.kb(24)
def test_an_order_from_pos01_reaches_the_kitchen_and_only_pos01_hears_back(
    kafka_bootstrap: str,
) -> None:
    """Scenario 24: Inventory reserves an order from POS01. The Kitchen receives the order
    through kitchen-orders; POS01 receives Reserved through its own status-events; other
    branches receive nothing.

    "Receives" is checked as the message on the branch's or the Kitchen's topic; the Kitchen
    and POS01 acting on it is the end-to-end version after step 6 (section 7 of document 02).
    "Nothing" is checked over a 5-second window after the expected messages arrived."""
    with psycopg.connect(INVENTORY_DB) as conn:
        for ingredient in ("BANH_MI", "THIT_LON"):
            assert receive_stock(conn, ingredient, D("1"))
    order_id = uuid.uuid4()
    env = order_created(
        order_id=order_id, created_at=datetime.now(UTC), items=[("BANH_MI_THIT", 1)]
    )

    tail = TopicTail(kafka_bootstrap, WATCHED)
    try:
        acked = Sender(kafka_bootstrap, "test-pos01").send_all(
            [Outgoing("order-events.POS01", str(order_id).encode(), encode(env))]
        )
        assert acked == [True]
        records: list[Record] = []
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            records += [r for r in tail.read(1) if r.key == str(order_id).encode()]
            if {r.topic for r in records} >= {"kitchen-orders", "status-events.POS01"}:
                break
        records += [r for r in tail.read(5) if r.key == str(order_id).encode()]  # stragglers
    finally:
        tail.close()

    by_topic = {t: [decode(r.value) for r in records if r.topic == t] for t in WATCHED}
    # The Kitchen receives the order through kitchen-orders.
    [kitchen] = by_topic["kitchen-orders"]
    assert kitchen.event_type == "OrderReserved"
    assert kitchen.order_id == order_id
    assert kitchen.causation_id == env.event_id
    assert kitchen.payload["origin_branch"] == "POS01"
    assert {r["ingredient_id"] for r in kitchen.payload["reserved"]} == {"BANH_MI", "THIT_LON"}
    # POS01 receives Reserved through its own status-events.
    [reserved] = by_topic["status-events.POS01"]
    assert reserved.event_type == "OrderReserved"
    assert reserved.causation_id == env.event_id
    # Other branches receive nothing.
    assert by_topic["status-events.POS02"] == []
    assert by_topic["status-events.ONLINE"] == []

    with psycopg.connect(INVENTORY_DB) as conn:
        record = conn.execute(
            "SELECT status, origin_branch FROM inventory_orders WHERE order_id = %s", (order_id,)
        ).fetchone()
        assert violations(conn) == {}
    assert record == ("DANG_GIU", "POS01")
