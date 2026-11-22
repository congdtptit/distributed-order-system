"""Inventory receives the Kitchen's commands (tier 1): release, waste, consumed, unmatched
commands. Table 3.3 and the stock accounting table of docs/01-business-spec.md, BR6, BR12,
Flow A; section 3 of docs/02-detailed-design.md."""

import uuid
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from inventory_support import (
    NOW,
    D,
    alerts,
    assert_invariants,
    deliver,
    line_outcomes,
    order_created,
    order_record,
    outbox,
    processed,
    release_requested,
    resend_with_new_event_id,
    reservations,
    seeded,
    set_available,
    stock,
    stock_consumed,
)

from common import reasons
from common.clock import FixedClock
from inventory_service.app import app, get_clock, get_conn

PHO_BO = {"BANH_PHO": D("0.2"), "THIT_BO": D("0.15"), "RAU_SONG": D("0.05")}


@pytest.fixture
def inv(migrated: Callable[[str], str]) -> str:
    return seeded(migrated("inventory-service"))


@pytest.fixture
def api(inv: str) -> Iterator[TestClient]:
    """The Inventory HTTP API on the test DB and a fixed clock (no Kafka, no workers)."""

    def conn() -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(inv) as c:
            yield c

    app.dependency_overrides[get_conn] = conn
    app.dependency_overrides[get_clock] = lambda: FixedClock(NOW)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def reserve(inv: str, items: list[tuple[str, int]] | None = None) -> Any:
    env = order_created(items=items or [("PHO_BO", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "DANG_GIU"
    return env


def dish_changes(inv: str) -> list[dict[str, Any]]:
    rows = [r for r in outbox(inv) if r.event_type == "DishStatusChanged"]
    assert {r.topic for r in rows} <= {"menu-events"}  # Flow C travels on menu-events
    return [r.payload | {"_key": r.key} for r in rows]


def dish_row(inv: str, dish_id: str) -> tuple[str, int, int]:
    with psycopg.connect(inv) as conn:
        row = conn.execute(
            "SELECT status, epoch, seq FROM dish_status WHERE dish_id = %s", (dish_id,)
        ).fetchone()
    assert row is not None
    return str(row[0]), int(row[1]), int(row[2])


def check_changed(inv: str) -> list[dict[str, Any]]:
    return [
        r.payload | {"_key": r.key} for r in outbox(inv) if r.event_type == "IngredientCheckChanged"
    ]


@pytest.mark.kb(5)
def test_a_release_command_arriving_three_times_adds_stock_once(inv: str) -> None:
    """Scenario 5: the release command for the same order reaches Inventory three times.
    Stock increases exactly once."""
    before = stock(inv)
    order = reserve(inv)
    release = release_requested(order.order_id)
    assert deliver(inv, release) is True
    sent = outbox(inv)
    assert deliver(inv, release) is False  # same event_id: blocked by processed_events
    assert (
        deliver(inv, resend_with_new_event_id(release)) is True
    )  # new event_id: record no longer Held
    assert outbox(inv) == sent  # neither duplicate emits anything
    after = stock(inv)
    for ingredient in PHO_BO:
        assert after[ingredient].available == before[ingredient].available  # back once, not more
        assert after[ingredient].reserved == 0
    assert order_record(inv, order.order_id) == ("DA_TRA", "EQUIPMENT_FAILURE", "POS01", NOW)
    assert set(line_outcomes(inv, order.order_id).values()) == {"DA_HOAN"}
    assert alerts(inv) == []  # a duplicate is not an unmatched command
    assert_invariants(inv)


@pytest.mark.kb(6)
def test_a_spoiled_ingredient_is_written_off_flagged_and_the_rest_released(inv: str) -> None:
    """Scenario 6, the Inventory part: the Kitchen rejects with the reason spoiled ingredient
    (meat). The meat is written off as waste and the other ingredients are released. Inventory
    also flags the meat and tells the Kitchen, which needs it for the ticket warning (step 4).
    Dishes that use meat move to Sold out (phase 2, Flow C)."""
    before = stock(inv)
    order = reserve(inv)
    deliver(
        inv,
        release_requested(order.order_id, reason=reasons.SPOILED_INGREDIENT, spoiled=["THIT_BO"]),
    )
    after = stock(inv)
    # The meat is written off as waste: out of reserved into wasted, not back to available.
    assert after["THIT_BO"].available == before["THIT_BO"].available - D("0.15")
    assert after["THIT_BO"].reserved == 0
    assert after["THIT_BO"].wasted == D("0.15")
    assert after["THIT_BO"].needs_check is True
    # The other ingredients are released.
    for ingredient in ("BANH_PHO", "RAU_SONG"):
        assert after[ingredient].available == before[ingredient].available
        assert after[ingredient].reserved == 0
        assert after[ingredient].wasted == 0
        assert after[ingredient].needs_check is False
    assert line_outcomes(inv, order.order_id) == {
        "BANH_PHO": "DA_HOAN",
        "RAU_SONG": "DA_HOAN",
        "THIT_BO": "HAO_HUT",
    }
    assert order_record(inv, order.order_id) == ("DA_TRA", reasons.SPOILED_INGREDIENT, "POS01", NOW)
    # Dishes that use meat move to Sold out: PHO_BO is the one dish with THIT_BO.
    assert dish_changes(inv) == [
        {"dish_id": "PHO_BO", "status": "HET", "epoch": 1, "seq": 1, "_key": "PHO_BO"}
    ]
    assert dish_row(inv, "PHO_BO") == ("HET", 1, 1)
    # The Kitchen is told the meat is flagged, with a version from menu_version. The dish took
    # seq 1: the dish_status rows are locked before menu_version (section 3 of document 02,
    # "Lock order"), so the dish change takes its version before the flag message does.
    assert check_changed(inv) == [
        {"ingredient_id": "THIT_BO", "needs_check": True, "epoch": 1, "seq": 2, "_key": "THIT_BO"}
    ]
    [row] = [r for r in outbox(inv) if r.event_type == "IngredientCheckChanged"]
    assert row.topic == "menu-events"
    assert_invariants(inv)


def test_writing_off_an_already_flagged_ingredient_announces_nothing_new(inv: str) -> None:
    first, second = reserve(inv), reserve(inv)
    for order in (first, second):
        deliver(
            inv,
            release_requested(
                order.order_id, reason=reasons.SPOILED_INGREDIENT, spoiled=["THIT_BO"]
            ),
        )
    assert stock(inv)["THIT_BO"].wasted == D("0.3")
    assert len(check_changed(inv)) == 1
    assert_invariants(inv)


@pytest.mark.kb(22)
def test_a_release_command_for_an_order_without_a_record_changes_no_stock(
    inv: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Scenario 22: Inventory receives a release command for an order that has no reservation
    record. Stock is unchanged and a log line is written (and an alerts row, section 3 of
    document 02)."""
    before = stock(inv)
    release = release_requested(order_created().order_id)
    with caplog.at_level("WARNING", logger="inventory_service.commands"):
        assert deliver(inv, release) is True
    assert stock(inv) == before
    assert order_record(inv, release.order_id) is None  # no record is created
    assert any(
        str(release.order_id) in r.message and str(release.event_id) in r.message
        for r in caplog.records
    )
    assert alerts(inv) == [("LENH_KHONG_KHOP", release.order_id, release.event_id)]
    assert processed(inv) == {release.event_id}
    assert_invariants(inv)


@pytest.mark.parametrize("command", ["release", "consumed"])
def test_a_command_reaching_a_failed_record_is_an_unmatched_command(inv: str, command: str) -> None:
    set_available(inv, "THIT_BO", D("0"))
    failed = order_created()
    deliver(inv, failed)
    before = stock(inv)
    msg = (
        release_requested(failed.order_id)
        if command == "release"
        else stock_consumed(failed.order_id)
    )
    deliver(inv, msg)
    assert stock(inv) == before
    assert order_record(inv, failed.order_id) == (
        "THAT_BAI",
        reasons.INSUFFICIENT_INGREDIENTS,
        "POS01",
        NOW,
    )
    assert alerts(inv) == [("LENH_KHONG_KHOP", failed.order_id, msg.event_id)]


@pytest.mark.kb(43)
def test_cooking_moves_the_reservation_to_consumed_without_touching_available(inv: str) -> None:
    """Scenario 43: Inventory has 10 kg of meat; an order reserves 2 kg, then the Kitchen
    presses Start cooking. Available stock is 8 kg before and after cooking; reserved returns
    to 0; consumed increases by 2 kg."""
    set_available(inv, "THIT_LON", D("10"))
    order = reserve(inv, [("BANH_MI_THIT", 25)])  # 25 x 0.08 kg = 2 kg of meat
    before_cooking = stock(inv)["THIT_LON"]
    assert (before_cooking.available, before_cooking.reserved) == (D("8"), D("2"))
    deliver(inv, stock_consumed(order.order_id))
    after = stock(inv)["THIT_LON"]
    assert after.available == D("8")
    assert after.reserved == 0
    assert after.consumed == before_cooking.consumed + D("2")
    assert order_record(inv, order.order_id) == ("DA_DUNG", None, "POS01", NOW)
    assert set(line_outcomes(inv, order.order_id).values()) == {"DA_DUNG"}
    assert_invariants(inv)


def test_after_cooking_a_release_is_ignored_and_a_second_consumed_too(inv: str) -> None:
    """Table 3.3: Released or Consumed, then a release command or a Consumed report: ignored."""
    order = reserve(inv)
    deliver(inv, stock_consumed(order.order_id))
    after_cooking = stock(inv)
    deliver(inv, release_requested(order.order_id))
    deliver(inv, resend_with_new_event_id(stock_consumed(order.order_id)))
    assert stock(inv) == after_cooking
    assert order_record(inv, order.order_id) == ("DA_DUNG", None, "POS01", NOW)
    assert alerts(inv) == []
    assert_invariants(inv)


@pytest.mark.kb(49)
def test_a_release_returns_the_quantity_recorded_at_reservation_not_the_new_recipe(
    inv: str,
) -> None:
    """Scenario 49: an order reserves 2 kg of meat; the dish's recipe changes to 3 kg; the
    Kitchen then cancels or rejects the order. Inventory releases exactly the 2 kg recorded at
    reservation time; available stock returns to what it was before the reservation."""
    set_available(inv, "THIT_LON", D("10"))
    before = stock(inv)["THIT_LON"]
    order = reserve(inv, [("BANH_MI_THIT", 25)])  # 2 kg
    reserved = stock(inv)["THIT_LON"]
    assert (reserved.available, reserved.reserved) == (D("8"), D("2"))
    with psycopg.connect(inv) as conn:  # the recipe changes: 25 portions would now need 3 kg
        changed = conn.execute(
            "UPDATE recipes SET quantity = 0.12"
            " WHERE dish_id = 'BANH_MI_THIT' AND ingredient_id = 'THIT_LON'"
        ).rowcount
    assert changed == 1
    deliver(
        inv, release_requested(order.order_id, reason=reasons.CHANGED_MIND, cancelled_by="CUSTOMER")
    )
    after = stock(inv)["THIT_LON"]
    assert after.available == before.available == D("10")
    assert after.reserved == 0
    assert_invariants(inv)


@pytest.mark.kb(48)
def test_clearing_the_flag_lets_a_new_order_reserve_the_ingredient_again(
    inv: str, api: TestClient
) -> None:
    """Scenario 48, the Inventory part: meat is flagged for stock check; Inventory confirms that
    the stock check is done. The flag is cleared; a new order that uses meat is reserved. The
    Kitchen is told (its warning disappears in step 4); dishes that use meat return to
    Available (phase 2, Flow C)."""
    spoiled = reserve(inv)
    deliver(
        inv,
        release_requested(spoiled.order_id, reason=reasons.SPOILED_INGREDIENT, spoiled=["THIT_BO"]),
    )
    blocked = order_created()
    deliver(inv, blocked)
    record = order_record(inv, blocked.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.AWAITING_STOCK_CHECK)

    response = api.post("/ingredients/THIT_BO/clear-check")
    assert response.status_code == 200
    # The flag is cleared ...
    assert response.json()["needs_check"] is False
    assert stock(inv)["THIT_BO"].needs_check is False
    # ... and announced to the Kitchen with a later version. Each flag message follows the
    # dish change of the same transaction (dish_status before menu_version, section 3 of
    # document 02): PHO_BO Sold out takes seq 1, the flag 2; PHO_BO back takes 3, the flag 4.
    assert [(c["needs_check"], c["seq"]) for c in check_changed(inv)] == [(True, 2), (False, 4)]
    # Dishes that use meat return to Available.
    assert [(d["dish_id"], d["status"], d["seq"]) for d in dish_changes(inv)] == [
        ("PHO_BO", "HET", 1),
        ("PHO_BO", "CON", 3),
    ]
    assert dish_row(inv, "PHO_BO") == ("CON", 1, 3)
    flag_rows = [r for r in outbox(inv) if r.event_type == "IngredientCheckChanged"]
    assert [(r.topic, r.key) for r in flag_rows] == [("menu-events", "THIT_BO")] * 2
    # A new order that uses meat is reserved.
    again = reserve(inv)
    assert reservations(inv, again.order_id) == PHO_BO
    assert_invariants(inv)


def test_clear_check_with_a_count_sets_available_to_on_hand_minus_reserved(
    inv: str, api: TestClient
) -> None:
    reserve(inv)  # THIT_BO reserved 0.15
    response = api.post("/ingredients/THIT_BO/clear-check", json={"counted_on_hand": "4.15"})
    assert response.status_code == 200
    assert Decimal(response.json()["available"]) == D("4")
    assert stock(inv)["THIT_BO"].available == D("4")
    assert check_changed(inv) == []  # the flag was not set, so nothing to announce
    assert_invariants(inv)


def test_clear_check_below_the_reserved_quantity_is_refused_and_changes_nothing(
    inv: str, api: TestClient
) -> None:
    reserve(inv)
    with psycopg.connect(inv) as conn:
        conn.execute("UPDATE stock SET needs_check = TRUE WHERE ingredient_id = 'THIT_BO'")
    before = stock(inv)
    response = api.post("/ingredients/THIT_BO/clear-check", json={"counted_on_hand": "0.1"})
    assert response.status_code == 409
    assert stock(inv) == before
    assert check_changed(inv) == []


def test_api_errors(api: TestClient) -> None:
    assert api.post("/ingredients/KHONG_CO/clear-check").status_code == 404
    assert (
        api.post("/ingredients/THIT_BO/clear-check", json={"counted_on_hand": "-1"}).status_code
        == 422
    )
    assert (
        api.post("/stock/receipts", json={"ingredient_id": "KHONG_CO", "quantity": "1"}).status_code
        == 404
    )
    assert (
        api.post("/stock/receipts", json={"ingredient_id": "THIT_BO", "quantity": "0"}).status_code
        == 422
    )


def test_stock_receipt_and_stock_list(inv: str, api: TestClient) -> None:
    before = stock(inv)["THIT_BO"].available
    response = api.post("/stock/receipts", json={"ingredient_id": "THIT_BO", "quantity": "2.5"})
    assert response.status_code == 200
    assert Decimal(response.json()["available"]) == before + D("2.5")
    listed = {i["ingredient_id"]: i for i in api.get("/stock").json()}
    assert listed["THIT_BO"]["name"] == "Thịt bò"
    assert Decimal(listed["THIT_BO"]["available"]) == before + D("2.5")
    assert set(listed["THIT_BO"]) == {
        "ingredient_id",
        "name",
        "unit",
        "available",
        "reserved",
        "consumed",
        "wasted",
        "needs_check",
    }


def test_a_malformed_spoiled_list_still_releases_the_order(inv: str) -> None:
    """A handler never raises for bad data (section 2 of document 02): the order is released
    and only what can be read is written off."""
    before = stock(inv)
    order = reserve(inv)
    bad = release_requested(order.order_id, reason=reasons.SPOILED_INGREDIENT)
    bad.payload["spoiled_ingredients"] = "THIT_BO"
    assert deliver(inv, bad) is True
    record = order_record(inv, order.order_id)
    assert record is not None and record[0] == "DA_TRA"
    assert stock(inv) == before  # everything released, nothing written off
    assert_invariants(inv)


def test_only_the_spoiled_reason_writes_anything_off(inv: str) -> None:
    """BR6: Inventory handles a release command according to its reason; equipment failure
    releases everything (Flow A step 5), even if the Kitchen sent an ingredient list."""
    before = stock(inv)
    order = reserve(inv)
    deliver(
        inv,
        release_requested(order.order_id, reason=reasons.EQUIPMENT_FAILURE, spoiled=["THIT_BO"]),
    )
    assert stock(inv) == before
    assert set(line_outcomes(inv, order.order_id).values()) == {"DA_HOAN"}
    assert check_changed(inv) == []
    assert_invariants(inv)


def test_kitchen_commands_on_a_branch_topic_are_refused(inv: str) -> None:
    """Section 13.2: a branch writing the Kitchen's command types to its own topic must not
    move stock; the message counts as unreadable (dlq)."""
    order = reserve(inv)
    held = stock(inv)
    for command in (release_requested(order.order_id), stock_consumed(order.order_id)):
        with pytest.raises(ValueError):
            deliver(inv, command, topic="order-events.POS01")
    assert stock(inv) == held
    record = order_record(inv, order.order_id)
    assert record is not None and record[0] == "DANG_GIU"


def test_alerts_api_lists_unmatched_commands(inv: str, api: TestClient) -> None:
    """``GET /alerts`` (section 6 of document 02): an unmatched release command's alert,
    newest first, filterable by ``kind``."""
    unknown = uuid.uuid4()
    assert deliver(inv, release_requested(unknown))
    body = api.get("/alerts").json()
    assert [(a["kind"], a["order_id"]) for a in body] == [("LENH_KHONG_KHOP", str(unknown))]
    assert body[0]["source_topic"] == "stock-commands"
    assert api.get("/alerts", params={"kind": "CAN_KIEM_TRA"}).json() == []
    assert api.get("/alerts", params={"kind": "HUY_SAI_CHI_NHANH"}).status_code == 422
