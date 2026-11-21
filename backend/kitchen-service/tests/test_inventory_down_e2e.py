"""Scenario 4 end to end (tier 3) on the running cluster: the order goes through the real
Inventory and Kitchen services, then every Inventory instance is stopped, the Kitchen rejects
the ticket through its HTTP API, and Inventory is started again."""

import json
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

import inventory_support as inv
import psycopg
import pytest

from common import reasons
from common.envelope import decode, encode
from common.kafka import Outgoing, Record, Sender, TopicTail
from inventory_service.invariants import violations
from inventory_service.stock import receive_stock

pytestmark = pytest.mark.tier3

INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
KITCHEN_DB = "postgresql://app:app@kitchen-db:5432/kitchen"
KITCHEN_API = "http://kitchen:8000"
STOCK_OF_TRA_DA = (
    "SELECT ingredient_id, available FROM stock WHERE ingredient_id IN ('LA_TRA', 'DA')"
)


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def stop(self, service: str) -> None: ...
    def start(self, service: str) -> None: ...
    def wait_healthy(self, service: str, timeout_s: float = 120) -> None: ...
    def health(self, service: str) -> str: ...


def wait_for(what: str, timeout_s: float, check: Any) -> Any:
    deadline = time.monotonic() + timeout_s
    while True:
        value = check()
        if value:
            return value
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.3)


def one(dsn: str, query: Any, *args: Any) -> Any:
    with psycopg.connect(dsn) as conn:
        row = conn.execute(query, args).fetchone()
    return None if row is None else row[0]


def running_inventories(chaos: Chaos) -> list[str]:
    found: list[str] = []
    for service in ("inventory-1", "inventory-2"):
        try:
            if chaos.health(service) == "healthy":
                found.append(service)
        except RuntimeError:  # inventory-2 exists only with --profile full
            pass
    return found


@pytest.mark.kb(4)
def test_kitchen_rejects_while_inventory_is_down_then_inventory_releases_once(
    kafka_bootstrap: str, chaos: Chaos
) -> None:
    """Scenario 4: the Kitchen rejects a ticket while Inventory is down, then Inventory comes
    back. The branch sees Cancelled immediately; Inventory releases exactly once when it comes
    back. "The branch sees" is checked as OrderCancelled on status-events.POS01; the branch
    applying it is step 6."""
    with psycopg.connect(INVENTORY_DB) as conn:
        for ingredient in ("LA_TRA", "DA"):
            assert receive_stock(conn, ingredient, inv.D("1"))
    with psycopg.connect(INVENTORY_DB) as conn:
        rows = conn.execute(STOCK_OF_TRA_DA).fetchall()
    before = {str(r[0]): r[1] for r in rows}

    order_id = uuid.uuid4()
    order = inv.order_created(
        order_id=order_id, created_at=datetime.now(UTC), items=[("TRA_DA", 1)]
    )
    assert Sender(kafka_bootstrap, "test-pos01").send_all(
        [Outgoing("order-events.POS01", str(order_id).encode(), encode(order))]
    ) == [True]
    wait_for(
        "the Queued ticket",
        60,
        lambda: (
            one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
            == "CHO_NAU"
        ),
    )

    # Inventory is down.
    stopped = running_inventories(chaos)
    assert stopped, "no Inventory instance is running"
    for service in stopped:
        chaos.stop(service)

    tail = TopicTail(kafka_bootstrap, ["status-events.POS01", "stock-commands"])
    try:
        request = urllib.request.Request(
            f"{KITCHEN_API}/tickets/{order_id}/reject",
            data=json.dumps({"reason_code": reasons.SHORT_STAFFED}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 200
        # The branch sees Cancelled immediately, with Inventory still down.
        seen: list[Record] = []
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not any(
            r.topic == "status-events.POS01" for r in seen
        ):
            seen += [r for r in tail.read(0.5) if r.key == str(order_id).encode()]
        cancelled = [decode(r.value) for r in seen if r.topic == "status-events.POS01"]
        assert [e.event_type for e in cancelled] == ["OrderCancelled"]
        assert cancelled[0].payload == {
            "cancelled_by": "KITCHEN",
            "reason_code": reasons.SHORT_STAFFED,
        }
        assert all(chaos.health(s) != "healthy" for s in stopped)
        assert (
            one(INVENTORY_DB, "SELECT status FROM inventory_orders WHERE order_id = %s", order_id)
            == "DANG_GIU"
        )

        # Inventory comes back and releases exactly once.
        for service in stopped:
            chaos.start(service)
        for service in stopped:
            chaos.wait_healthy(service)
        wait_for(
            "Inventory to release",
            90,
            lambda: (
                one(
                    INVENTORY_DB,
                    "SELECT status FROM inventory_orders WHERE order_id = %s",
                    order_id,
                )
                == "DA_TRA"
            ),
        )
        seen += [r for r in tail.read(5) if r.key == str(order_id).encode()]
    finally:
        tail.close()

    releases = [
        r
        for r in seen
        if r.topic == "stock-commands" and decode(r.value).event_type == "ReleaseRequested"
    ]
    assert len(releases) == 1
    with psycopg.connect(INVENTORY_DB) as conn:
        outcomes = conn.execute(
            "SELECT outcome FROM inventory_reservations WHERE order_id = %s", (order_id,)
        ).fetchall()
        rows = conn.execute(STOCK_OF_TRA_DA).fetchall()
        assert violations(conn) == {}
    assert {r[0] for r in outcomes} == {"DA_HOAN"}
    assert {str(r[0]): r[1] for r in rows} == before  # released once: back to the start, not above
