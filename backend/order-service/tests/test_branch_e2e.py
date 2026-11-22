"""The branch end to end on the running cluster (tier 3): orders placed through the ``pos01``
container's HTTP API travel through the real Kafka, Inventory and Kitchen. Losing the network
is ``bin/chaos offline pos01``: the container is cut off ``kafka-net`` through the Docker
Engine API and keeps its DB and API."""

import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

import inventory_support as inv
import psycopg
import pytest

from common.envelope import decode
from common.kafka import Record, TopicTail
from inventory_service.invariants import violations
from inventory_service.stock import receive_stock
from order_service.statuses import CANCEL_REJECTED_MESSAGE

pytestmark = pytest.mark.tier3

POS01 = "http://pos01:8000"
KITCHEN = "http://kitchen:8000"
INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
KITCHEN_DB = "postgresql://app:app@kitchen-db:5432/kitchen"


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def disconnect(self, service: str, network: str = "kafka-net") -> None: ...
    def connect(self, service: str, network: str = "kafka-net") -> None: ...
    def stop(self, service: str) -> None: ...
    def start(self, service: str) -> None: ...
    def wait_healthy(self, service: str, timeout_s: float = 120) -> None: ...
    def health(self, service: str) -> str: ...


def http(method: str, url: str, body: Any = None) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_for(what: str, timeout_s: float, check: Callable[[], Any]) -> Any:
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


def stock_for_tra_da(portions: int) -> None:
    """Enough tea and ice whatever earlier tests used (TRA_DA: LA_TRA and DA)."""
    with psycopg.connect(INVENTORY_DB) as conn:
        for ingredient in ("LA_TRA", "DA"):
            assert receive_stock(conn, ingredient, inv.D(portions))


def place_at_pos01() -> dict[str, Any]:
    status, order = http(
        "POST", f"{POS01}/orders", {"items": [{"dish_id": "TRA_DA", "quantity": 1}]}
    )
    assert status == 201, order
    return order


def pos01_order(order_id: str) -> dict[str, Any]:
    status, order = http("GET", f"{POS01}/orders/{order_id}")
    assert status == 200, order
    return order


def _probed_after(at: str, *, connected: bool) -> bool:
    connection = http("GET", f"{POS01}/monitor")[1]["connection"]
    checked = connection["checked_at"]
    return (
        connection["connected"] is connected
        and checked is not None
        and datetime.fromisoformat(checked) > datetime.fromisoformat(at)
    )


def assert_inventory_invariants() -> None:
    with psycopg.connect(INVENTORY_DB) as conn:
        assert violations(conn) == {}


def go_offline(chaos: Chaos) -> None:
    chaos.disconnect("pos01")
    wait_for(
        "pos01 to see Kafka unreachable",
        30,
        lambda: http("GET", f"{POS01}/monitor")[1]["connection"]["connected"] is False,
    )


def go_online(chaos: Chaos) -> None:
    chaos.connect("pos01")
    wait_for(
        "pos01 to see Kafka again",
        60,
        lambda: http("GET", f"{POS01}/monitor")[1]["connection"]["connected"] is True,
    )


@pytest.mark.kb(24)
def test_an_order_placed_at_pos01_becomes_reserved_through_its_own_status_topic(
    kafka_bootstrap: str,
) -> None:
    """Scenario 24 end to end: Inventory reserves an order from POS01; the Kitchen gets it
    through kitchen-orders, POS01 gets Reserved through status-events.POS01, and the other
    branches' status topics get nothing for it."""
    stock_for_tra_da(1)
    tail = TopicTail(kafka_bootstrap, ["status-events.POS02", "status-events.ONLINE"])
    try:
        order = place_at_pos01()
        assert (order["status"], order["send_state"]) == ("CHO_KHO", "CHUA_GUI")
        reserved = wait_for(
            "Reserved at POS01", 60, lambda: pos01_order(order["order_id"])["status"] == "DA_GIU"
        )
        assert reserved
        assert pos01_order(order["order_id"])["send_state"] == "DA_GUI"
        wait_for(
            "the Queued ticket",
            30,
            lambda: (
                one(
                    KITCHEN_DB,
                    "SELECT status FROM kitchen_orders WHERE order_id = %s",
                    order["order_id"],
                )
                == "CHO_NAU"
            ),
        )
        others = [r for r in tail.read(3) if r.key == order["order_id"].encode()]
        assert others == []
    finally:
        tail.close()
    assert_inventory_invariants()


@pytest.mark.kb(10)
def test_an_order_cancelled_while_offline_is_never_sent(kafka_bootstrap: str, chaos: Chaos) -> None:
    """Scenario 10: POS01 is offline, so the sender does not set the flag; the cashier creates
    an order and cancels it; the network comes back. POS01 closes the order as Cancelled at
    once and sends nothing: Inventory and the Kitchen have no record of it. A second order
    created offline and not cancelled is sent when the network returns."""
    stock_for_tra_da(1)
    go_offline(chaos)
    cancelled = place_at_pos01()
    kept = place_at_pos01()
    # A probe made after both orders existed has failed: the sender looked at their entries
    # and left them without the flag.
    wait_for(
        "a failed probe after the orders were placed",
        30,
        lambda: _probed_after(kept["created_at"], connected=False),
    )
    assert pos01_order(cancelled["order_id"])["send_state"] == "CHUA_GUI"
    status, body = http(
        "POST", f"{POS01}/orders/{cancelled['order_id']}/cancel", {"reason_code": "CHANGED_MIND"}
    )
    assert status == 200, body
    assert (body["status"], body["send_state"]) == ("DA_HUY", None)
    _, monitor = http("GET", f"{POS01}/monitor")
    assert monitor["waiting_to_send"] == 1  # the kept order

    tail = TopicTail(kafka_bootstrap, ["order-events.POS01"])
    try:
        go_online(chaos)
        wait_for(
            "the kept order to be Reserved",
            60,
            lambda: pos01_order(kept["order_id"])["status"] == "DA_GIU",
        )
        sent: list[Record] = tail.read(2)
    finally:
        tail.close()
    keys = {r.key for r in sent}
    assert kept["order_id"].encode() in keys
    assert cancelled["order_id"].encode() not in keys
    assert {decode(r.value).order_id for r in sent} == {uuid.UUID(kept["order_id"])}
    for dsn, table in ((INVENTORY_DB, "inventory_orders"), (KITCHEN_DB, "kitchen_orders")):
        found = one(dsn, f"SELECT count(*) FROM {table} WHERE order_id = %s", cancelled["order_id"])
        assert found == 0, f"{table} has the cancelled order"
    assert pos01_order(cancelled["order_id"])["status"] == "DA_HUY"
    assert_inventory_invariants()


@pytest.mark.kb(36)
def test_a_cancel_sent_after_reconnecting_reaches_a_cooking_ticket(chaos: Chaos) -> None:
    """Scenario 36: POS01 sends the order, then goes offline, and the cashier presses cancel;
    the Kitchen presses Start cooking before the cancel request arrives. POS01 sees "Cannot
    cancel: the kitchen has started cooking"; the order continues to Completed; the
    ingredients are consumed, not released."""
    stock_for_tra_da(1)
    order = place_at_pos01()
    order_id = order["order_id"]
    wait_for("Reserved at POS01", 60, lambda: pos01_order(order_id)["status"] == "DA_GIU")
    wait_for(
        "the Queued ticket",
        30,
        lambda: (
            one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
            == "CHO_NAU"
        ),
    )

    go_offline(chaos)
    status, body = http(
        "POST", f"{POS01}/orders/{order_id}/cancel", {"reason_code": "WAITED_TOO_LONG"}
    )
    assert status == 202, body
    assert (body["cancel_flag"], body["cancel_send_state"]) == ("DANG_YEU_CAU", "CHUA_GUI")
    status, body = http("POST", f"{KITCHEN}/tickets/{order_id}/start")
    assert status == 200, body

    go_online(chaos)
    refused = wait_for(
        "POS01 to show the refusal",
        60,
        lambda: (o := pos01_order(order_id))["cancel_message"] == CANCEL_REJECTED_MESSAGE and o,
    )
    assert (refused["status"], refused["cancel_flag"]) == ("DA_GIU", "KHONG")

    status, body = http("POST", f"{KITCHEN}/tickets/{order_id}/complete")
    assert status == 200, body
    wait_for("Completed at POS01", 60, lambda: pos01_order(order_id)["status"] == "HOAN_TAT")
    wait_for(
        "Inventory to count the order consumed",
        60,
        lambda: (
            one(INVENTORY_DB, "SELECT status FROM inventory_orders WHERE order_id = %s", order_id)
            == "DA_DUNG"
        ),
    )
    with psycopg.connect(INVENTORY_DB) as conn:
        outcomes = conn.execute(
            "SELECT outcome FROM inventory_reservations WHERE order_id = %s", (order_id,)
        ).fetchall()
    assert outcomes and {r[0] for r in outcomes} == {"DA_DUNG"}  # none released
    assert_inventory_invariants()


def running_inventories(chaos: Chaos) -> list[str]:
    running: list[str] = []
    for service in ("inventory-1", "inventory-2"):
        try:
            if chaos.health(service) == "healthy":
                running.append(service)
        except RuntimeError:  # inventory-2 exists only with --profile full
            pass
    return running


def stock_of(ingredients: tuple[str, ...]) -> dict[str, Any]:
    with psycopg.connect(INVENTORY_DB) as conn:
        rows = conn.execute(
            "SELECT ingredient_id, available, reserved FROM stock WHERE ingredient_id = ANY(%s)",
            (list(ingredients),),
        ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def line_outcomes(order_id: str) -> list[Any]:
    with psycopg.connect(INVENTORY_DB) as conn:
        rows = conn.execute(
            "SELECT outcome FROM inventory_reservations WHERE order_id = %s", (order_id,)
        ).fetchall()
    return [r[0] for r in rows]


@pytest.mark.kb(1)
def test_a_cancel_that_reaches_the_kitchen_before_the_order(chaos: Chaos) -> None:
    """Scenario 1, one of the demo scenarios: Inventory is down, so the order waits in
    order-events while the cashier's cancel request reaches the Kitchen first. Inventory then
    reserves the ingredients and forwards the order. No ticket; the order is Cancelled;
    Inventory releases in full, once."""
    stock_for_tra_da(1)
    stopped = running_inventories(chaos)
    assert stopped, "no Inventory instance is running"
    try:
        for service in stopped:
            chaos.stop(service)
        before = stock_of(("LA_TRA", "DA"))
        order = place_at_pos01()
        order_id = order["order_id"]
        wait_for(
            "the order to be sent", 30, lambda: pos01_order(order_id)["send_state"] == "DA_GUI"
        )
        status, body = http(
            "POST", f"{POS01}/orders/{order_id}/cancel", {"reason_code": "CHANGED_MIND"}
        )
        assert status == 202, body
        # The cancel request reaches the Kitchen before the order: a Cancel-pending record,
        # and POS01 hears "the kitchen will not cook".
        wait_for(
            "the Kitchen's Cancel-pending record",
            30,
            lambda: (
                one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
                == "HUY_CHO_DON"
            ),
        )
        wait_for(
            "POS01 to show the kitchen will not cook",
            30,
            lambda: pos01_order(order_id)["cancel_flag"] == "BEP_KHONG_NAU",
        )
        assert pos01_order(order_id)["status"] == "CHO_KHO"
    finally:
        for service in stopped:
            chaos.start(service)
        for service in stopped:
            chaos.wait_healthy(service)

    # Inventory reserves, the Kitchen cancels instead of queuing, Inventory releases.
    wait_for("Cancelled at POS01", 60, lambda: pos01_order(order_id)["status"] == "DA_HUY")
    wait_for(
        "Inventory to release the order",
        60,
        lambda: (
            one(INVENTORY_DB, "SELECT status FROM inventory_orders WHERE order_id = %s", order_id)
            == "DA_TRA"
        ),
    )
    # No ticket: the Kitchen record went from Cancel-pending to Cancelled, never Queued.
    assert (
        one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
        == "DA_HUY"
    )
    status, tickets = http("GET", f"{KITCHEN}/tickets")
    assert status == 200
    assert order_id not in {t["order_id"] for t in tickets}
    # Inventory releases in full, once: every line released, and the stock is back where it was.
    outcomes = line_outcomes(order_id)
    assert outcomes and set(outcomes) == {"DA_HOAN"}
    assert stock_of(("LA_TRA", "DA")) == before
    final = pos01_order(order_id)
    assert (final["close_reason"], final["cancel_flag"]) == ("CHANGED_MIND", "KHONG")
    assert_inventory_invariants()


@pytest.mark.kb(3)
def test_cancel_and_start_cooking_pressed_together_agree_everywhere() -> None:
    """Scenario 3, one of the demo scenarios: the cashier presses cancel and the Kitchen presses
    Start cooking at the same time. Exactly one wins, and the branch, the Kitchen and Inventory
    agree. The cancel travels through Kafka while Start cooking is a direct call, so the start
    is held back by a different delay each round; any round may go either way, and each must
    be consistent. The many-run race on two connections is the Kitchen's tier 2 test."""
    for delay_s in (0.0, 0.05, 0.15, 0.3, 0.6):
        race_round(delay_s)


def race_round(delay_s: float) -> None:
    """One round of scenario 3, with Start cooking held back by ``delay_s``."""
    stock_for_tra_da(1)
    order = place_at_pos01()
    order_id = order["order_id"]
    wait_for("Reserved at POS01", 60, lambda: pos01_order(order_id)["status"] == "DA_GIU")
    wait_for(
        "the Queued ticket",
        30,
        lambda: (
            one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
            == "CHO_NAU"
        ),
    )
    answers: dict[str, int] = {}
    barrier = threading.Barrier(2)

    def cancel() -> None:
        barrier.wait()
        answers["cancel"] = http(
            "POST", f"{POS01}/orders/{order_id}/cancel", {"reason_code": "WAITED_TOO_LONG"}
        )[0]

    def start(delay: float = delay_s) -> None:
        barrier.wait()
        time.sleep(delay)
        answers["start"] = http("POST", f"{KITCHEN}/tickets/{order_id}/start")[0]

    threads = [threading.Thread(target=cancel), threading.Thread(target=start)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert answers["cancel"] == 202  # the order was sent: the Kitchen decides
    assert answers["start"] in (200, 409), answers

    if answers["start"] == 200:
        # Start cooking won: the cancel is refused, the order goes on and is consumed.
        refused = wait_for(
            "POS01 to show the refusal",
            60,
            lambda: (o := pos01_order(order_id))["cancel_message"] == CANCEL_REJECTED_MESSAGE and o,
        )
        assert (refused["status"], refused["cancel_flag"]) == ("DA_GIU", "KHONG")
        assert (
            one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
            == "DANG_NAU"
        )
        wait_for(
            "Inventory to count the order consumed",
            60,
            lambda: (
                one(
                    INVENTORY_DB,
                    "SELECT status FROM inventory_orders WHERE order_id = %s",
                    order_id,
                )
                == "DA_DUNG"
            ),
        )
        assert set(line_outcomes(order_id)) == {"DA_DUNG"}
        status, _ = http("POST", f"{KITCHEN}/tickets/{order_id}/complete")
        assert status == 200
        wait_for("Completed at POS01", 60, lambda: pos01_order(order_id)["status"] == "HOAN_TAT")
    else:
        # The cancel won: the ticket is Cancelled, the order too, and Inventory releases.
        wait_for("Cancelled at POS01", 60, lambda: pos01_order(order_id)["status"] == "DA_HUY")
        assert (
            one(KITCHEN_DB, "SELECT status FROM kitchen_orders WHERE order_id = %s", order_id)
            == "DA_HUY"
        )
        wait_for(
            "Inventory to release the order",
            60,
            lambda: (
                one(
                    INVENTORY_DB,
                    "SELECT status FROM inventory_orders WHERE order_id = %s",
                    order_id,
                )
                == "DA_TRA"
            ),
        )
        assert set(line_outcomes(order_id)) == {"DA_HOAN"}
    assert_inventory_invariants()
