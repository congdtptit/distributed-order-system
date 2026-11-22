"""Placing an order at the branch (tier 1): base flow step 1 and BR9 of
docs/01-business-spec.md; ``POST /orders``, ``GET /orders``, ``GET /dishes`` in section 6 of
docs/02-detailed-design.md. The order the branch queues is handed to Inventory's real handler,
and Inventory's answer back to the branch's."""

import uuid
from collections.abc import Callable
from typing import Any

import inventory_support as inv
import kitchen_support as kit
import psycopg
import pytest
from branch_support import NOW, deliver, entries, order_row, queued_envelope
from fastapi.testclient import TestClient

from common.seed import load_menu
from order_service.app import app, get_branch
from order_service.orders import load_dishes


def place(api: TestClient, items: list[dict[str, Any]]) -> dict[str, Any]:
    response = api.post("/orders", json={"items": items})
    assert response.status_code == 201, response.text
    return response.json()


def test_an_order_is_stored_awaiting_inventory_with_its_create_order_entry(
    api: TestClient, bdb: str
) -> None:
    order = place(api, [{"dish_id": "PHO_BO", "quantity": 2}, {"dish_id": "TRA_DA", "quantity": 1}])
    order_id = uuid.UUID(order["order_id"])
    assert order["status"] == "CHO_KHO"
    assert order["cancel_flag"] == "KHONG"
    assert order["send_state"] == "CHUA_GUI"  # "Not sent, kitchen has not received it" (BR5)
    assert order["cancel_send_state"] is None
    assert order["created_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert order["items"] == [
        {"dish_id": "PHO_BO", "name": "Phở bò", "quantity": 2},
        {"dish_id": "TRA_DA", "name": "Trà đá", "quantity": 1},
    ]

    [entry] = entries(bdb, order_id)
    assert (entry["kind"], entry["topic"], entry["attempted"], entry["sent_at"]) == (
        "TAO_DON",
        "order-events.POS01",
        False,
        None,
    )
    env = queued_envelope(bdb, order_id)
    assert (env.event_type, env.order_id, env.branch_id) == ("OrderCreated", order_id, "POS01")
    assert env.payload == {
        "created_at": NOW.isoformat(),
        "channel": "POS",
        "items": order["items"],
    }
    assert entry["payload"]["event_id"] == str(env.event_id)


@pytest.mark.parametrize(
    "body",
    [
        {"items": []},
        {},
        {"items": [{"dish_id": "PHO_BO"}]},
        {"items": [{"quantity": 1}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": 0}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": -1}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": 1.5}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": "2"}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": True}]},
        {"items": [{"dish_id": "PHO_BO", "quantity": 1}, {"dish_id": "KHONG_CO", "quantity": 1}]},
    ],
)
def test_invalid_order_data_is_refused_with_400_and_enters_no_queue(
    api: TestClient, bdb: str, body: dict[str, Any]
) -> None:
    """BR9: a missing field, a quantity that is not a positive whole number, or a dish not in
    ``dishes``: HTTP 400, nothing stored."""
    response = api.post("/orders", json=body)
    assert response.status_code == 400, response.text
    assert api.get("/orders").json() == []
    assert entries(bdb) == []


def test_the_online_branch_queues_channel_online_on_its_own_topic(
    api: TestClient, bdb: str
) -> None:
    app.dependency_overrides[get_branch] = lambda: "ONLINE"
    order = place(api, [{"dish_id": "PHO_BO", "quantity": 1}])
    order_id = uuid.UUID(order["order_id"])
    assert order["branch_id"] == "ONLINE"
    [entry] = entries(bdb, order_id)
    assert entry["topic"] == "order-events.ONLINE"
    assert queued_envelope(bdb, order_id).payload["channel"] == "ONLINE"


def test_reading_orders(api: TestClient) -> None:
    first = place(api, [{"dish_id": "PHO_BO", "quantity": 1}])
    assert [o["order_id"] for o in api.get("/orders").json()] == [first["order_id"]]
    assert api.get(f"/orders/{first['order_id']}").json() == first
    assert api.get(f"/orders/{uuid.uuid4()}").status_code == 404
    assert api.get("/orders/not-a-uuid").status_code == 400


def test_dishes_come_from_the_seed_file_and_reload_on_every_start(
    api: TestClient, bdb: str
) -> None:
    menu = load_menu()
    assert api.get("/dishes").json() == sorted(
        ({"dish_id": d.dish_id, "name": d.name} for d in menu.dishes),
        key=lambda d: d["dish_id"],
    )
    with psycopg.connect(bdb) as conn:
        conn.execute("UPDATE dishes SET name = 'old name' WHERE dish_id = 'PHO_BO'")
        conn.commit()
        load_dishes(conn, menu)  # the next start
    assert {d["dish_id"]: d["name"] for d in api.get("/dishes").json()}["PHO_BO"] == "Phở bò"


@pytest.mark.kb(24)
def test_inventory_accepts_the_branch_order_and_its_answer_reaches_the_branch(
    api: TestClient, bdb: str, migrated: Callable[[str], str]
) -> None:
    """Scenario 24, branch side: the order the branch queues is the order Inventory reserves;
    Inventory's ``OrderReserved`` on ``status-events.POS01`` moves the branch to Reserved, and
    the Kitchen gets its ticket from Inventory's ``kitchen-orders`` message."""
    idb = inv.seeded(migrated("inventory-service"))
    kdb = migrated("kitchen-service")
    order_id = uuid.UUID(place(api, [{"dish_id": "PHO_BO", "quantity": 1}])["order_id"])

    to_kitchen = kit.through_inventory(idb, queued_envelope(bdb, order_id))
    assert to_kitchen.event_type == "OrderReserved"
    [answer] = kit.sent_envelopes(idb, "OrderReserved", "status-events.POS01")
    assert answer.order_id == order_id
    assert deliver(bdb, answer)
    row = order_row(bdb, order_id)
    assert row is not None and row["status"] == "DA_GIU"

    assert kit.deliver(kdb, to_kitchen)
    ticket = kit.record(kdb, order_id)
    assert ticket is not None and ticket["status"] == "CHO_NAU"
    inv.assert_invariants(idb)


def test_reading_only_the_newest_orders(api: TestClient) -> None:
    """The screen asks for a page of the newest orders instead of all 200 every 2 seconds."""
    for _ in range(3):
        place(api, [{"dish_id": "PHO_BO", "quantity": 1}])
    everything = [o["order_id"] for o in api.get("/orders").json()]
    assert len(everything) == 3
    assert [o["order_id"] for o in api.get("/orders?limit=2").json()] == everything[:2]
    for bad in ("0", "201", "x"):
        assert api.get(f"/orders?limit={bad}").status_code == 400
