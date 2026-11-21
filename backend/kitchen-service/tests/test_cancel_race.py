"""Cancel races at the Kitchen (tier 2): two operations on two connections released together,
many times. Where the scenario names Inventory, its real handler gets the Kitchen's command, so
the agreement between the sides is checked on both DBs."""

import threading
import uuid
from collections.abc import Callable
from typing import Any

import inventory_support as inv
import psycopg
import pytest
from kitchen_support import (
    cancel_requested,
    deliver,
    order_reserved,
    outbox,
    record,
    sent_envelopes,
    through_inventory,
)

from common import reasons
from common.clock import FixedClock
from kitchen_service.tickets import ActionError, reject, start_cooking

RUNS = 60
CLOCK = FixedClock(inv.NOW)


def race(actions: list[Callable[[], None]]) -> list[str]:
    """Run the actions at the same moment; each result is "won", or the HTTP code of the
    refusal (ActionError), or "done" for a message handler (it never refuses)."""
    barrier = threading.Barrier(len(actions))
    results = [""] * len(actions)

    def run(i: int) -> None:
        barrier.wait()
        try:
            actions[i]()
            results[i] = "won"
        except ActionError as exc:
            results[i] = str(exc.status_code)
        except BaseException as exc:  # anything else is a failure, not a lost race
            results[i] = f"error: {exc!r}"

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(actions))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not [r for r in results if not r or r.startswith("error")], results
    return results


def button(
    conn: psycopg.Connection[Any], press: Callable[[psycopg.Connection[Any]], object]
) -> Callable[[], None]:
    def act() -> None:
        with conn.transaction():
            press(conn)

    return act


def message(kdb: str, conn: psycopg.Connection[Any], env: Any) -> Callable[[], None]:
    def act() -> None:
        deliver(kdb, env, conn=conn)

    return act


@pytest.fixture
def conns(migrated: Callable[[str], str]) -> Any:
    kdb = migrated("kitchen-service")
    idb = inv.seeded(migrated("inventory-service"))
    pair = [psycopg.connect(kdb, autocommit=True) for _ in range(2)]
    yield kdb, idb, pair
    for c in pair:
        c.close()


def refill(idb: str) -> None:
    inv.set_available(idb, "LA_TRA", inv.D("1"))
    inv.set_available(idb, "DA", inv.D("10"))


def commands_for(kdb: str, order_id: uuid.UUID | None) -> list[Any]:
    return [
        e
        for e in sent_envelopes(kdb, "ReleaseRequested") + sent_envelopes(kdb, "StockConsumed")
        if e.order_id == order_id
    ]


@pytest.mark.kb(3)
def test_cancel_and_start_cooking_at_the_same_time_one_wins_and_all_sides_agree(conns: Any) -> None:
    """Scenario 3: the cashier presses cancel and the Kitchen presses Start cooking at the same
    time. Exactly one operation wins; the statuses at the Kitchen, Inventory and the branch
    agree. The branch's side is what the Kitchen sends it (OrderCancelled or CancelRejected);
    the branch applying it is step 6."""
    kdb, idb, pair = conns
    wins = {"cancel": 0, "cook": 0}
    for _ in range(RUNS):
        refill(idb)
        order = inv.order_created(items=[("TRA_DA", 1)])
        deliver(kdb, through_inventory(idb, order))
        assert order.order_id is not None
        request = cancel_requested(order.order_id)
        results = race(
            [
                message(kdb, pair[0], request),
                button(pair[1], lambda c, o=order.order_id: start_cooking(c, o, CLOCK)),
            ]
        )
        rec = record(kdb, order.order_id)
        assert rec is not None
        to_branch = [
            s
            for s in outbox(kdb)
            if s.key == str(order.order_id) and s.topic == "status-events.POS01"
        ]
        if results[1] == "won":  # cooking won: the cancel request found it Cooking
            wins["cook"] += 1
            assert rec["status"] == "DANG_NAU"
            assert [s.event_type for s in to_branch] == ["CancelRejected"]
        else:  # the cancel won: the button was refused
            wins["cancel"] += 1
            assert results[1] == "409"
            assert rec["status"] == "DA_HUY"
            assert [s.event_type for s in to_branch] == ["OrderCancelled"]
        # Exactly one command reaches Inventory, and Inventory ends where the Kitchen did.
        commands = commands_for(kdb, order.order_id)
        assert len(commands) == 1
        inv.deliver(idb, commands[0])
        inv_rec = inv.order_record(idb, order.order_id)
        assert inv_rec is not None and inv_rec[0] == (
            "DA_DUNG" if rec["status"] == "DANG_NAU" else "DA_TRA"
        )
        inv.assert_invariants(idb)
    assert wins["cancel"] > 0 and wins["cook"] > 0, wins


@pytest.mark.kb(28)
def test_order_and_cancel_request_at_two_instances_at_the_same_time_give_one_record(
    conns: Any,
) -> None:
    """Scenario 28: two Kitchen instances run; both receive the order and the cancel request for
    the same order ID at the same time. Only one record exists; the result matches table 3.2
    whichever message arrives first: Cancelled either way, with "kitchen will not cook" first
    only when the cancel request came first, and one release command."""
    kdb, _idb, pair = conns
    seen = {"order first": 0, "cancel first": 0}
    for _ in range(100):
        order = order_reserved()
        assert order.order_id is not None
        race(
            [message(kdb, pair[0], order), message(kdb, pair[1], cancel_requested(order.order_id))]
        )
        with psycopg.connect(kdb) as conn:
            count = conn.execute(
                "SELECT count(*) FROM kitchen_orders WHERE order_id = %s", (order.order_id,)
            ).fetchone()
        assert count == (1,)
        rec = record(kdb, order.order_id)
        assert rec is not None and (rec["status"], rec["cancelled_by"]) == ("DA_HUY", "CUSTOMER")
        sent = [(s.topic, s.event_type) for s in outbox(kdb) if s.key == str(order.order_id)]
        result = [("stock-commands", "ReleaseRequested"), ("status-events.POS01", "OrderCancelled")]
        if sent[0][1] == "CancelPending":
            seen["cancel first"] += 1
            assert sent == [("status-events.POS01", "CancelPending"), *result]
        else:
            seen["order first"] += 1
            assert sent == result
    assert seen["order first"] > 0 and seen["cancel first"] > 0, seen


@pytest.mark.kb(51)
def test_spoiled_reject_and_the_origin_cancel_at_the_same_time_one_release_by_the_winner(
    conns: Any,
) -> None:
    """Scenario 51: staff press Reject with the reason spoiled ingredient at the very moment the
    origin branch's cancel request reaches a Queued ticket. Exactly one operation wins;
    Inventory processes exactly one release command, according to the winner's reason: either
    release everything, or write off as waste and flag for stock check."""
    kdb, idb, pair = conns
    wins = {"reject": 0, "cancel": 0}
    for _ in range(RUNS):
        refill(idb)
        with psycopg.connect(idb, autocommit=True) as c:  # each run starts unflagged
            c.execute("UPDATE stock SET needs_check = FALSE WHERE ingredient_id = 'DA'")
        order = inv.order_created(items=[("TRA_DA", 1)])
        deliver(kdb, through_inventory(idb, order))
        assert order.order_id is not None
        wasted_before = inv.stock(idb)["DA"].wasted
        results = race(
            [
                message(kdb, pair[0], cancel_requested(order.order_id)),
                button(
                    pair[1],
                    lambda c, o=order.order_id: reject(
                        c, o, reasons.SPOILED_INGREDIENT, ["DA"], CLOCK
                    ),
                ),
            ]
        )
        rec = record(kdb, order.order_id)
        assert rec is not None and rec["status"] == "DA_HUY"
        [release] = [
            e for e in sent_envelopes(kdb, "ReleaseRequested") if e.order_id == order.order_id
        ]
        inv.deliver(idb, release)
        after = inv.stock(idb)["DA"]
        if results[1] == "won":  # the rejection won: write off and flag
            wins["reject"] += 1
            assert rec["cancelled_by"] == "KITCHEN"
            assert release.payload["reason_code"] == reasons.SPOILED_INGREDIENT
            assert (after.wasted - wasted_before, after.needs_check) == (inv.D("0.3"), True)
        else:  # the cancel won: release everything
            wins["cancel"] += 1
            assert results[1] == "409" and rec["cancelled_by"] == "CUSTOMER"
            assert (after.wasted - wasted_before, after.needs_check) == (0, False)
            # Release everything: the record leaves Held and every line goes back to stock.
            inv_rec = inv.order_record(idb, order.order_id)
            assert inv_rec is not None and inv_rec[0] == "DA_TRA"
            assert set(inv.line_outcomes(idb, order.order_id).values()) == {"DA_HOAN"}
        inv.assert_invariants(idb)
    assert wins["reject"] > 0 and wins["cancel"] > 0, wins
