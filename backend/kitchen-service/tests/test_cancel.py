"""Cancel requests at the Kitchen (tier 1): table 3.2 of docs/01-business-spec.md and its order
of precedence, the Kitchen decision table of Flow B (section 6), section 13.2; section 4 of
docs/02-detailed-design.md. Where Inventory takes part, its real handler runs on its own DB."""

import uuid
from collections.abc import Callable
from typing import Any

import inventory_support as inv
import psycopg
import pytest
from kitchen_support import (
    alerts,
    cancel_requested,
    deliver,
    order_failed,
    order_reserved,
    outbox,
    record,
    sent_envelopes,
    through_inventory,
)

from common import reasons
from common.clock import FixedClock
from kitchen_service.tickets import list_tickets, start_cooking

NOW = inv.NOW


@pytest.fixture
def kdb(migrated: Callable[[str], str]) -> str:
    return migrated("kitchen-service")


@pytest.fixture
def idb(migrated: Callable[[str], str]) -> str:
    return inv.seeded(migrated("inventory-service"))


def sent(kdb: str) -> list[tuple[str, str, dict[str, Any]]]:
    return [(s.topic, s.event_type, s.payload) for s in outbox(kdb)]


def no_tickets(kdb: str) -> bool:
    with psycopg.connect(kdb) as conn:
        return list_tickets(conn) == []


def release_at_inventory(kdb: str, idb: str) -> None:
    """Hand every release command the Kitchen wrote to Inventory's real handler."""
    for release in sent_envelopes(kdb, "ReleaseRequested"):
        inv.deliver(idb, release)


@pytest.mark.kb(1)
def test_a_cancel_request_before_the_order_cancels_it_on_arrival_and_inventory_releases_once(
    kdb: str, idb: str
) -> None:
    """Scenario 1: a cancel request reaches the Kitchen before the order; Inventory then
    reserves the ingredients and forwards the order to the Kitchen. No ticket; the order is
    Cancelled; Inventory releases in full, once."""
    before = inv.stock(idb)
    order = inv.order_created()
    deliver(kdb, cancel_requested(order.order_id, reason=reasons.CHANGED_MIND))
    # Not Cancelled yet: the order has not arrived (prohibition 5); the branch gets the
    # commitment "kitchen will not cook".
    rec = record(kdb, order.order_id)
    assert rec is not None and rec["status"] == "HUY_CHO_DON"
    assert sent(kdb) == [("status-events.POS01", "CancelPending", {})]

    deliver(kdb, through_inventory(idb, order))
    # No ticket; the order is Cancelled.
    assert no_tickets(kdb)
    rec = record(kdb, order.order_id)
    assert rec is not None
    assert (rec["status"], rec["cancelled_by"], rec["close_reason"]) == (
        "DA_HUY",
        "CUSTOMER",
        reasons.CHANGED_MIND,
    )
    assert sent(kdb)[1:] == [
        (
            "stock-commands",
            "ReleaseRequested",
            {
                "cancelled_by": "CUSTOMER",
                "reason_code": reasons.CHANGED_MIND,
                "spoiled_ingredients": [],
            },
        ),
        (
            "status-events.POS01",
            "OrderCancelled",
            {"cancelled_by": "CUSTOMER", "reason_code": reasons.CHANGED_MIND},
        ),
    ]
    # Inventory releases in full, once.
    release_at_inventory(kdb, idb)
    assert inv.stock(idb) == before
    inv_rec = inv.order_record(idb, order.order_id)
    assert inv_rec is not None and inv_rec[0] == "DA_TRA"
    assert set(inv.line_outcomes(idb, order.order_id).values()) == {"DA_HOAN"}
    inv.assert_invariants(idb)


@pytest.mark.kb(2)
def test_the_order_arriving_again_after_a_cancel_creates_no_ticket_and_no_second_release(
    kdb: str, idb: str
) -> None:
    """Scenario 2: as scenario 1, then Inventory sends the order a second time. No ticket is
    created and no second release command is sent. Both kinds of repeat: the same message
    (same event_id) and the order in a new message."""
    order = inv.order_created()
    deliver(kdb, cancel_requested(order.order_id))
    to_kitchen = through_inventory(idb, order)
    deliver(kdb, to_kitchen)
    sent_once = len(outbox(kdb))

    assert deliver(kdb, to_kitchen) is False  # same event_id: blocked
    assert len(outbox(kdb)) == sent_once
    again = inv.resend_with_new_event_id(to_kitchen)
    deliver(kdb, again)  # new event_id: the stored result, not a second release
    assert no_tickets(kdb)
    assert [e.event_type for e in sent_envelopes(kdb, "ReleaseRequested")] == ["ReleaseRequested"]
    replies = outbox(kdb)[sent_once:]
    assert [(r.topic, r.event_type, r.causation_id) for r in replies] == [
        ("status-events.POS01", "OrderCancelled", str(again.event_id))
    ]
    rec = record(kdb, order.order_id)
    assert rec is not None and rec["status"] == "DA_HUY"
    release_at_inventory(kdb, idb)
    inv_rec = inv.order_record(idb, order.order_id)
    assert inv_rec is not None and inv_rec[0] == "DA_TRA"
    inv.assert_invariants(idb)


@pytest.mark.kb(8)
def test_a_cancel_pending_order_failed_by_inventory_ends_failed(kdb: str, idb: str) -> None:
    """Scenario 8: an order that has a Cancel-pending record is rejected by Inventory. The
    branch sees Failed and the cancel flag turns off; the Kitchen record moves to Failed.
    The branch applying Failed (and turning its flag off) is in the branch's test_cancel.py;
    here: Inventory's
    OrderFailed to the branch, and the Kitchen's record."""
    inv.set_available(idb, "THIT_BO", inv.D("0"))
    order = inv.order_created()
    deliver(kdb, cancel_requested(order.order_id))
    pending = record(kdb, order.order_id)
    assert pending is not None and pending["status"] == "HUY_CHO_DON"
    deliver(kdb, through_inventory(idb, order))
    rec = record(kdb, order.order_id)
    assert rec is not None
    assert (rec["status"], rec["close_reason"]) == ("THAT_BAI", reasons.INSUFFICIENT_INGREDIENTS)
    inv.assert_invariants(idb)
    # The branch hears Failed from Inventory ...
    [to_branch] = sent_envelopes(idb, "OrderFailed", "status-events.POS01")
    assert to_branch.payload["reason_code"] == reasons.INSUFFICIENT_INGREDIENTS
    # ... and the Kitchen sends nothing more: no Cancelled, no release command.
    assert sent(kdb) == [("status-events.POS01", "CancelPending", {})]


@pytest.mark.kb(23)
def test_a_cancel_request_while_cooking_is_refused(kdb: str) -> None:
    """Scenario 23: a cancel request arrives while the ticket is Cooking. The branch sees
    "Cannot cancel: the kitchen has started cooking" and the status is unchanged. "The branch
    sees" is checked as CancelRejected on status-events.POS01; the branch showing it is in
    the branch's test_cancel.py."""
    env = order_reserved()
    deliver(kdb, env)
    assert env.order_id is not None
    with psycopg.connect(kdb) as conn:
        start_cooking(conn, env.order_id, FixedClock(NOW))
    deliver(kdb, cancel_requested(env.order_id))
    rec = record(kdb, env.order_id)
    assert rec is not None and rec["status"] == "DANG_NAU"
    assert sent(kdb) == [
        ("stock-commands", "StockConsumed", {}),
        ("status-events.POS01", "CancelRejected", {"kitchen_status": "DANG_NAU"}),
    ]


def test_a_cancel_request_on_a_completed_ticket_is_refused_too(kdb: str) -> None:
    env = order_reserved()
    deliver(kdb, env)
    assert env.order_id is not None
    with psycopg.connect(kdb, autocommit=True) as conn:
        conn.execute(
            "UPDATE kitchen_orders SET status = 'HOAN_TAT' WHERE order_id = %s", (env.order_id,)
        )
    deliver(kdb, cancel_requested(env.order_id))
    assert sent(kdb) == [("status-events.POS01", "CancelRejected", {"kitchen_status": "HOAN_TAT"})]


def test_a_cancel_request_on_a_queued_ticket_cancels_it(kdb: str) -> None:
    """Table 3.2: Queued, cancel request from the origin branch → Cancelled (customer)."""
    env = order_reserved()
    deliver(kdb, env)
    deliver(kdb, cancel_requested(env.order_id, reason=reasons.WAITED_TOO_LONG))
    rec = record(kdb, env.order_id)
    assert rec is not None
    assert (rec["status"], rec["cancelled_by"], rec["close_reason"]) == (
        "DA_HUY",
        "CUSTOMER",
        reasons.WAITED_TOO_LONG,
    )
    assert [e for _, e, _ in sent(kdb)] == ["ReleaseRequested", "OrderCancelled"]


@pytest.mark.kb(27)
def test_a_cancel_from_another_branch_on_a_ticket_is_ignored_with_a_warning(kdb: str) -> None:
    """Scenario 27: POS01 sends a cancel request for an order of POS02 that already has a
    ticket at the Kitchen. The Kitchen ignores the request and raises a warning; the POS02
    order does not change status."""
    env = order_reserved(origin="POS02")
    deliver(kdb, env)
    deliver(kdb, cancel_requested(env.order_id, branch="POS01"))
    rec = record(kdb, env.order_id)
    assert rec is not None and rec["status"] == "CHO_NAU"
    assert rec["cancel_branches"] == []
    assert alerts(kdb) == [
        ("HUY_SAI_CHI_NHANH", env.order_id, {"origin_branch": "POS02", "dismissed": ["POS01"]})
    ]
    assert sent(kdb) == []  # no reply to anyone (section 4 of document 02)


def test_a_cancel_from_another_branch_on_a_terminal_record_is_ignored_too(kdb: str) -> None:
    env = order_failed(origin="POS02")
    deliver(kdb, env)
    deliver(kdb, cancel_requested(env.order_id, branch="POS01"))
    assert [a[0] for a in alerts(kdb)] == ["HUY_SAI_CHI_NHANH"]
    assert sent(kdb) == []


@pytest.mark.kb(33)
def test_failed_first_then_the_cancel_request_gets_failed_and_no_cancel_pending(kdb: str) -> None:
    """Scenario 33: Inventory's Failed report reaches the Kitchen first, and the cancel request
    for that order arrives later. The Kitchen has a Failed record; no Cancel-pending record is
    created; the branch sees Failed. "The branch sees" is checked as OrderFailed on
    status-events.POS01; the branch applying it is in the branch's test_cancel.py."""
    failed = order_failed(reason=reasons.ORDER_EXPIRED)
    deliver(kdb, failed)
    request = cancel_requested(failed.order_id)
    deliver(kdb, request)
    rec = record(kdb, failed.order_id)
    assert rec is not None
    assert (rec["status"], rec["cancel_branches"]) == ("THAT_BAI", [])
    assert [(r.topic, r.event_type, r.payload, r.causation_id) for r in outbox(kdb)] == [
        (
            "status-events.POS01",
            "OrderFailed",
            {"origin_branch": "POS01", "reason_code": reasons.ORDER_EXPIRED},
            str(request.event_id),
        )
    ]


@pytest.mark.kb(34)
def test_a_wrong_branch_cancel_before_the_order_is_dismissed_when_the_order_arrives(
    kdb: str,
) -> None:
    """Scenario 34: POS02 sends a cancel request for an order ID of POS01 before the order
    reaches the Kitchen. The POS01 order still gets a Queued ticket; the POS02 request is
    dismissed; a warning is raised."""
    order_id = uuid.uuid4()
    deliver(kdb, cancel_requested(order_id, branch="POS02"))
    rec = record(kdb, order_id)
    assert rec is not None and (rec["status"], rec["cancel_branches"]) == ("HUY_CHO_DON", ["POS02"])
    assert sent(kdb) == [("status-events.POS02", "CancelPending", {})]  # to the branch that asked

    deliver(kdb, order_reserved(order_id, origin="POS01"))
    rec = record(kdb, order_id)
    assert rec is not None
    assert (rec["status"], rec["cancel_branches"], rec["cancel_reasons"]) == ("CHO_NAU", [], {})
    assert alerts(kdb) == [
        ("HUY_SAI_CHI_NHANH", order_id, {"origin_branch": "POS01", "dismissed": ["POS02"]})
    ]
    assert len(outbox(kdb)) == 1  # nothing more is sent


@pytest.mark.kb(35)
def test_the_origin_branch_cancelling_too_before_the_order_cancels_it(kdb: str, idb: str) -> None:
    """Scenario 35: as scenario 34, but POS01 also sends a cancel request before the order
    arrives. The order is Cancelled; Inventory releases exactly once."""
    before = inv.stock(idb)
    order = inv.order_created()
    deliver(
        kdb, cancel_requested(order.order_id, branch="POS02", reason=reasons.WRONG_ORDER_ENTERED)
    )
    deliver(kdb, cancel_requested(order.order_id, branch="POS01", reason=reasons.WAITED_TOO_LONG))
    rec = record(kdb, order.order_id)
    assert rec is not None and rec["cancel_branches"] == ["POS02", "POS01"]

    deliver(kdb, through_inventory(idb, order))
    rec = record(kdb, order.order_id)
    assert rec is not None
    # Cancelled with the origin branch's own reason, not the other branch's.
    assert (rec["status"], rec["cancelled_by"], rec["close_reason"]) == (
        "DA_HUY",
        "CUSTOMER",
        reasons.WAITED_TOO_LONG,
    )
    # Each branch gets its commitment; only the origin branch gets Cancelled.
    assert [(r.topic, r.event_type) for r in outbox(kdb)] == [
        ("status-events.POS02", "CancelPending"),
        ("status-events.POS01", "CancelPending"),
        ("stock-commands", "ReleaseRequested"),
        ("status-events.POS01", "OrderCancelled"),
    ]
    release_at_inventory(kdb, idb)
    assert len(sent_envelopes(kdb, "ReleaseRequested")) == 1
    assert inv.stock(idb) == before
    inv.assert_invariants(idb)


def test_a_repeated_cancel_request_gets_the_commitment_again_and_keeps_the_first_reason(
    kdb: str,
) -> None:
    order_id = uuid.uuid4()
    first = cancel_requested(order_id, reason=reasons.CHANGED_MIND)
    deliver(kdb, first)
    assert deliver(kdb, first) is False  # same event_id: nothing
    deliver(kdb, cancel_requested(order_id, reason=reasons.WAITED_TOO_LONG))  # new message
    rec = record(kdb, order_id)
    assert rec is not None
    assert (rec["cancel_branches"], rec["cancel_reasons"]) == (
        ["POS01"],
        {"POS01": reasons.CHANGED_MIND},
    )
    assert sent(kdb) == [("status-events.POS01", "CancelPending", {})] * 2


def test_a_cancel_request_on_a_cancelled_order_gets_the_stored_result(kdb: str) -> None:
    env = order_reserved()
    deliver(kdb, env)
    deliver(kdb, cancel_requested(env.order_id))
    deliver(kdb, cancel_requested(env.order_id))
    assert [e for _, e, _ in sent(kdb)] == ["ReleaseRequested", "OrderCancelled", "OrderCancelled"]


def test_inventory_messages_on_a_branch_topic_are_refused(kdb: str) -> None:
    """Section 13.2: a branch writing Inventory's message types to its own topic (a bug or a
    misconfiguration) must not decide an order; the message counts as unreadable (dlq)."""
    order_id = uuid.uuid4()
    with pytest.raises(ValueError):
        deliver(kdb, order_failed(order_id, origin="POS02"), topic="cancel-events.POS02")
    with pytest.raises(ValueError):
        deliver(kdb, order_reserved(order_id, origin="POS02"), topic="cancel-events.POS02")
    assert record(kdb, order_id) is None
    deliver(kdb, order_reserved(order_id))  # the real one still queues a ticket
    rec = record(kdb, order_id)
    assert rec is not None and rec["status"] == "CHO_NAU"


def test_a_cancel_on_a_failed_record_without_origin_answers_the_asking_branch(kdb: str) -> None:
    """Table 3.2, last row: the stored result. A malformed OrderFailed leaves no origin, so the
    answer goes to the branch that asked."""
    failed = order_failed()
    failed.payload.pop("origin_branch")
    deliver(kdb, failed)
    deliver(kdb, cancel_requested(failed.order_id, branch="ONLINE"))
    assert [(r.topic, r.event_type) for r in outbox(kdb)] == [
        ("status-events.ONLINE", "OrderFailed")
    ]


def test_a_reason_outside_the_customer_group_is_not_used(kdb: str) -> None:
    env = order_reserved()
    deliver(kdb, env)
    deliver(kdb, cancel_requested(env.order_id, reason=reasons.SPOILED_INGREDIENT))
    rec = record(kdb, env.order_id)
    assert rec is not None and rec["close_reason"] == reasons.CHANGED_MIND
    [release] = sent_envelopes(kdb, "ReleaseRequested")
    assert release.payload["spoiled_ingredients"] == []


def test_a_repeat_fills_in_a_missing_reason(kdb: str) -> None:
    order_id = uuid.uuid4()
    first = cancel_requested(order_id)
    first.payload.pop("reason_code")
    deliver(kdb, first)
    deliver(kdb, cancel_requested(order_id, reason=reasons.WAITED_TOO_LONG))
    deliver(kdb, cancel_requested(order_id, reason=reasons.CHANGED_MIND))
    rec = record(kdb, order_id)
    assert rec is not None and rec["cancel_reasons"] == {"POS01": reasons.WAITED_TOO_LONG}
