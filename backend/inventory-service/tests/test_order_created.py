"""Inventory receives OrderCreated (tier 1): table 3.3 of docs/01-business-spec.md, BR1, BR6,
BR11, BR12; section 3 of docs/02-detailed-design.md. Messages go through ``handle_once``, the
same deduplication as the consumer."""

from collections.abc import Callable
from datetime import timedelta

import psycopg
import pytest
from inventory_support import (
    NOW,
    D,
    assert_invariants,
    deliver,
    flag_for_stock_check,
    order_created,
    order_record,
    outbox,
    processed,
    resend_with_new_event_id,
    reservations,
    seeded,
    set_available,
    stock,
)

from common import reasons
from inventory_service.stock import receive_stock


@pytest.fixture
def inv(migrated: Callable[[str], str]) -> str:
    """A seeded Inventory DB (backend/seed/menu.json): PHO_BO needs BANH_PHO 0.2, THIT_BO 0.15
    and RAU_SONG 0.05."""
    return seeded(migrated("inventory-service"))


def test_an_order_with_enough_stock_is_reserved_and_sent_to_the_kitchen_and_the_branch(
    inv: str,
) -> None:
    before = stock(inv)
    env = order_created(items=[("PHO_BO", 2), ("TRA_DA", 1)])
    assert deliver(inv, env) is True

    after = stock(inv)
    demand = {
        "BANH_PHO": D("0.4"),
        "THIT_BO": D("0.3"),
        "RAU_SONG": D("0.1"),
        "LA_TRA": D("0.005"),
        "DA": D("0.3"),
    }
    for ingredient, q in demand.items():
        assert after[ingredient].available == before[ingredient].available - q
        assert after[ingredient].reserved == q
    assert reservations(inv, env.order_id) == demand
    assert order_record(inv, env.order_id) == ("DANG_GIU", None, "POS01", NOW)

    kitchen, branch = outbox(inv)
    assert (kitchen.topic, kitchen.event_type, kitchen.key) == (
        "kitchen-orders",
        "OrderReserved",
        str(env.order_id),
    )
    assert kitchen.payload["origin_branch"] == "POS01"
    assert kitchen.payload["created_at"] == env.payload["created_at"]
    assert kitchen.payload["items"] == env.payload["items"]
    assert sorted(kitchen.payload["reserved"], key=lambda r: r["ingredient_id"]) == [
        {"ingredient_id": "BANH_PHO", "name": "Bánh phở", "unit": "kg", "quantity": 0.4},
        {"ingredient_id": "DA", "name": "Đá", "unit": "kg", "quantity": 0.3},
        {"ingredient_id": "LA_TRA", "name": "Lá trà", "unit": "kg", "quantity": 0.005},
        {"ingredient_id": "RAU_SONG", "name": "Rau sống", "unit": "kg", "quantity": 0.1},
        {"ingredient_id": "THIT_BO", "name": "Thịt bò", "unit": "kg", "quantity": 0.3},
    ]
    assert (branch.topic, branch.event_type, branch.payload) == (
        "status-events.POS01",
        "OrderReserved",
        {},
    )
    for row in (kitchen, branch):
        assert row.causation_id == str(env.event_id)
        assert row.branch_id == "POS01"
    assert kitchen.event_id != branch.event_id
    assert_invariants(inv)


def test_the_origin_branch_comes_from_the_topic_not_from_branch_id(inv: str) -> None:
    env = order_created(branch_id="POS02")
    deliver(inv, env, topic="order-events.ONLINE")
    record = order_record(inv, env.order_id)
    assert record is not None and record[2] == "ONLINE"
    assert [r.topic for r in outbox(inv)] == ["kitchen-orders", "status-events.ONLINE"]
    assert outbox(inv)[0].payload["origin_branch"] == "ONLINE"


@pytest.mark.kb(30)
def test_short_of_one_ingredient_then_resent_gets_the_stored_result(inv: str) -> None:
    """Scenario 30: Inventory is short of one ingredient when reserving an order, then the
    message for that order is resent. Stock is unchanged; the Failed record, the
    processed_events row and the Failed message are all stored; the resend gets the same
    stored result."""
    set_available(inv, "THIT_BO", D("0.1"))  # PHO_BO needs 0.15
    before = stock(inv)
    env = order_created()
    assert deliver(inv, env) is True

    # Stock is unchanged, including the ingredients that were not short (BR1).
    assert stock(inv) == before
    assert reservations(inv, env.order_id) == {}
    # The Failed record, the processed_events row and the Failed message are all stored.
    assert order_record(inv, env.order_id) == (
        "THAT_BAI",
        reasons.INSUFFICIENT_INGREDIENTS,
        "POS01",
        NOW,
    )
    assert processed(inv) == {env.event_id}
    failed = outbox(inv)
    assert [(r.topic, r.event_type) for r in failed] == [
        ("kitchen-orders", "OrderFailed"),
        ("status-events.POS01", "OrderFailed"),
    ]
    for row in failed:
        assert row.payload == {
            "origin_branch": "POS01",
            "reason_code": reasons.INSUFFICIENT_INGREDIENTS,
        }

    # Resent with the same event_id: blocked by processed_events, nothing emitted.
    assert deliver(inv, env) is False
    assert outbox(inv) == failed

    # Resent with a new event_id: the same stored result, to the origin branch only.
    again = resend_with_new_event_id(env)
    assert deliver(inv, again) is True
    new_rows = outbox(inv)[len(failed) :]
    assert [(r.topic, r.event_type, r.payload) for r in new_rows] == [
        (
            "status-events.POS01",
            "OrderFailed",
            {"origin_branch": "POS01", "reason_code": reasons.INSUFFICIENT_INGREDIENTS},
        )
    ]
    assert new_rows[0].causation_id == str(again.event_id)
    assert new_rows[0].event_id not in {r.event_id for r in failed}
    assert stock(inv) == before
    assert order_record(inv, env.order_id) == (
        "THAT_BAI",
        reasons.INSUFFICIENT_INGREDIENTS,
        "POS01",
        NOW,
    )
    assert_invariants(inv)


@pytest.mark.kb(9)
def test_failed_for_lack_of_stock_then_restocked_then_resent_fails_again(inv: str) -> None:
    """Scenario 9: Inventory returns Failed for lack of stock, more stock is received, then the
    order is resent. Inventory returns Failed again and reserves nothing."""
    set_available(inv, "THIT_BO", D("0.1"))
    env = order_created()
    deliver(inv, env)
    assert order_record(inv, env.order_id) == (
        "THAT_BAI",
        reasons.INSUFFICIENT_INGREDIENTS,
        "POS01",
        NOW,
    )

    with psycopg.connect(inv) as conn:
        assert receive_stock(conn, "THIT_BO", D("5"))
    restocked = stock(inv)
    # The restock now covers the order: PHO_BO needs 0.15 of THIT_BO.
    assert restocked["THIT_BO"].available == D("5.1")
    sent_before = len(outbox(inv))

    for resend in (env, resend_with_new_event_id(env)):  # both kinds of duplicate
        deliver(inv, resend)
        # Failed again ...
        assert order_record(inv, env.order_id) == (
            "THAT_BAI",
            reasons.INSUFFICIENT_INGREDIENTS,
            "POS01",
            NOW,
        )
        # ... and nothing is reserved.
        assert stock(inv) == restocked
        assert reservations(inv, env.order_id) == {}
    replies = outbox(inv)[sent_before:]
    assert [(r.topic, r.event_type, r.payload["reason_code"]) for r in replies] == [
        ("status-events.POS01", "OrderFailed", reasons.INSUFFICIENT_INGREDIENTS)
    ]
    assert_invariants(inv)


@pytest.mark.kb(15)
def test_an_order_older_than_x_hours_fails_as_expired(inv: str) -> None:
    """Scenario 15: POS is offline for longer than X and then sends the old order. Inventory
    returns Failed (order expired) and reserves no ingredients."""
    before = stock(inv)
    old = order_created(created_at=NOW - timedelta(hours=4, minutes=1))
    deliver(inv, old)
    assert order_record(inv, old.order_id) == (
        "THAT_BAI",
        reasons.ORDER_EXPIRED,
        "POS01",
        NOW - timedelta(hours=4, minutes=1),
    )
    assert [(r.topic, r.event_type, r.payload["reason_code"]) for r in outbox(inv)] == [
        ("kitchen-orders", "OrderFailed", reasons.ORDER_EXPIRED),
        ("status-events.POS01", "OrderFailed", reasons.ORDER_EXPIRED),
    ]
    assert stock(inv) == before
    assert reservations(inv, old.order_id) == {}
    assert_invariants(inv)


def test_an_order_exactly_x_hours_old_is_still_accepted(inv: str) -> None:
    """BR11 fails an order created *more* than X hours ago."""
    env = order_created(created_at=NOW - timedelta(hours=4))
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "DANG_GIU"


@pytest.mark.kb(16)
def test_an_order_created_one_hour_in_the_future_fails(inv: str) -> None:
    """Scenario 16: an order has a creation time 1 hour in the future. Inventory returns
    Failed."""
    before = stock(inv)
    future = order_created(created_at=NOW + timedelta(hours=1))
    deliver(inv, future)
    record = order_record(inv, future.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.FUTURE_CREATION_TIME)
    assert [(r.topic, r.event_type, r.payload["reason_code"]) for r in outbox(inv)] == [
        ("kitchen-orders", "OrderFailed", reasons.FUTURE_CREATION_TIME),
        ("status-events.POS01", "OrderFailed", reasons.FUTURE_CREATION_TIME),
    ]
    assert stock(inv) == before
    assert_invariants(inv)


def test_a_creation_time_within_the_tolerance_is_accepted(inv: str) -> None:
    env = order_created(created_at=NOW + timedelta(minutes=4))
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "DANG_GIU"


@pytest.mark.kb(39)
def test_a_readable_order_with_a_negative_quantity_fails_as_invalid_data(inv: str) -> None:
    """Scenario 39: Inventory receives an order that is readable but has a negative quantity.
    Inventory writes a Failed record (invalid order data) and reserves nothing; the branch sees
    Failed; the message does not go to dlq."""
    before = stock(inv)
    env = order_created(items=[("PHO_BO", -1)])
    # Handled like any message: no exception, so the consumer does not count a failed attempt
    # and the message never reaches the dlq.
    assert deliver(inv, env) is True
    assert processed(inv) == {env.event_id}
    # A Failed record with the reason; no readable creation time is kept.
    assert order_record(inv, env.order_id) == (
        "THAT_BAI",
        reasons.INVALID_ORDER_DATA,
        "POS01",
        None,
    )
    # Nothing reserved.
    assert stock(inv) == before
    assert reservations(inv, env.order_id) == {}
    # The branch sees Failed (and the Kitchen is told, table 3.3).
    assert [(r.topic, r.event_type, r.payload) for r in outbox(inv)] == [
        (
            "kitchen-orders",
            "OrderFailed",
            {"origin_branch": "POS01", "reason_code": reasons.INVALID_ORDER_DATA},
        ),
        (
            "status-events.POS01",
            "OrderFailed",
            {"origin_branch": "POS01", "reason_code": reasons.INVALID_ORDER_DATA},
        ),
    ]
    assert_invariants(inv)


@pytest.mark.parametrize(
    "payload",
    [
        {"channel": "POS", "items": [{"dish_id": "PHO_BO", "quantity": 1}]},
        {
            "created_at": "yesterday",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": 1}],
        },
        {
            "created_at": "2026-11-20T09:15:00",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": 1}],
        },
        {
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "FAX",
            "items": [{"dish_id": "PHO_BO", "quantity": 1}],
        },
        {"created_at": "2026-11-20T09:15:00Z", "channel": "POS", "items": []},
        {"created_at": "2026-11-20T09:15:00Z", "channel": "POS", "items": [{"quantity": 1}]},
        {
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": 0}],
        },
        {
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": 1.5}],
        },
        {
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": "1"}],
        },
        {
            "created_at": "2026-11-20T09:15:00Z",
            "channel": "POS",
            "items": [{"dish_id": "PHO_BO", "quantity": True}],
        },
        {"created_at": "2026-11-20T09:15:00Z", "channel": "POS", "items": ["PHO_BO"]},
    ],
    ids=[
        "no-created-at",
        "bad-time",
        "naive-time",
        "bad-channel",
        "no-items",
        "no-dish",
        "zero",
        "fraction",
        "string",
        "bool",
        "not-an-object",
    ],
)
def test_other_invalid_order_data_also_fails_without_dlq(
    inv: str, payload: dict[str, object]
) -> None:
    before = stock(inv)
    env = order_created(payload=payload)
    assert deliver(inv, env) is True
    record = order_record(inv, env.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.INVALID_ORDER_DATA)
    assert stock(inv) == before


@pytest.mark.kb(44)
def test_a_flagged_ingredient_is_not_reserved_even_with_enough_stock(inv: str) -> None:
    """Scenario 44: meat is flagged for stock check and available stock is sufficient; POS,
    while offline, still accepts an order with a dish that uses meat and then sends it.
    Inventory returns Failed (ingredient awaiting stock check); no ingredient of the order is
    reserved."""
    flag_for_stock_check(inv, "THIT_BO")
    before = stock(inv)
    assert before["THIT_BO"].available >= D("0.15")  # enough stock
    env = order_created(items=[("PHO_BO", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.AWAITING_STOCK_CHECK)
    assert [(r.topic, r.event_type, r.payload["reason_code"]) for r in outbox(inv)] == [
        ("kitchen-orders", "OrderFailed", reasons.AWAITING_STOCK_CHECK),
        ("status-events.POS01", "OrderFailed", reasons.AWAITING_STOCK_CHECK),
    ]
    # No ingredient of the order is reserved: BANH_PHO comes before THIT_BO in lock order and
    # was deducted first, then undone with the savepoint.
    assert stock(inv) == before
    assert reservations(inv, env.order_id) == {}
    assert_invariants(inv)


def test_a_flagged_ingredient_decides_the_reason_even_when_another_is_short(inv: str) -> None:
    """BR6: an order that needs a flagged ingredient gets Failed (awaiting stock check). Here
    BANH_PHO (first in lock order) is short and THIT_BO is flagged."""
    set_available(inv, "BANH_PHO", D("0.1"))
    flag_for_stock_check(inv, "THIT_BO")
    env = order_created(items=[("PHO_BO", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.AWAITING_STOCK_CHECK)


def test_an_unflagged_dish_still_reserves_while_another_ingredient_is_flagged(inv: str) -> None:
    flag_for_stock_check(inv, "THIT_BO")
    env = order_created(items=[("BUN_CHA", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "DANG_GIU"


def test_a_dish_with_no_recipe_fails_and_reserves_nothing(inv: str) -> None:
    before = stock(inv)
    env = order_created(items=[("PHO_BO", 1), ("MON_DA_XOA", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.NO_RECIPE)
    assert stock(inv) == before
    assert_invariants(inv)


def test_a_demand_beyond_any_stock_fails_as_insufficient(inv: str) -> None:
    env = order_created(items=[("PHO_BO", 10**15)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[:2] == ("THAT_BAI", reasons.INSUFFICIENT_INGREDIENTS)


def test_a_held_order_resent_with_a_new_event_id_returns_reserved_without_a_second_reservation(
    inv: str,
) -> None:
    env = order_created()
    deliver(inv, env)
    after_first = stock(inv)
    sent = len(outbox(inv))
    deliver(inv, resend_with_new_event_id(env))
    replies = outbox(inv)[sent:]
    # Only to the origin branch, not to the Kitchen again (section 3 of document 02).
    assert [(r.topic, r.event_type, r.payload) for r in replies] == [
        ("status-events.POS01", "OrderReserved", {})
    ]
    assert stock(inv) == after_first
    assert reservations(inv, env.order_id) == {
        "BANH_PHO": D("0.2"),
        "THIT_BO": D("0.15"),
        "RAU_SONG": D("0.05"),
    }
    assert_invariants(inv)
