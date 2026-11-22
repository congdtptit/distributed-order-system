"""The branch applies status messages by rank (tier 1): section 3.1 of
docs/01-business-spec.md and BR3; the table "The branch applies status messages as follows" and
writes (3) to (5) of docs/02-detailed-design.md.

Messages are fed straight into the branch's handlers through ``handle_once``, the same
deduplication the consumer runs.
"""

import uuid

import pytest
from branch_support import (
    cancel,
    deliver,
    mark_attempted,
    order_row,
    place,
    processed,
    status_message,
)

from common.envelope import Envelope
from order_service.statuses import CANCEL_REJECTED_MESSAGE


def requested(bdb: str) -> uuid.UUID:
    """An attempted order with a cancel request waiting: the flag is ``DANG_YEU_CAU``."""
    order_id = place(bdb)
    mark_attempted(bdb, order_id)
    assert not cancel(bdb, order_id)
    return order_id


def status(bdb: str, order_id: uuid.UUID) -> tuple[str, int, str | None, str]:
    row = order_row(bdb, order_id)
    assert row is not None
    return row["status"], row["status_rank"], row["close_reason"], row["cancel_flag"]


def resent(env: Envelope) -> Envelope:
    """The same result in a new message: how the Kitchen and Inventory return a stored result."""
    return Envelope(
        event_id=uuid.uuid4(),
        event_type=env.event_type,
        order_id=env.order_id,
        branch_id=env.branch_id,
        occurred_at=env.occurred_at,
        payload=env.payload,
    )


def test_statuses_move_forward_reserved_then_completed(bdb: str) -> None:
    order_id = place(bdb)
    assert status(bdb, order_id) == ("CHO_KHO", 0, None, "KHONG")
    deliver(bdb, status_message("OrderReserved", order_id))
    assert status(bdb, order_id) == ("DA_GIU", 1, None, "KHONG")
    deliver(bdb, status_message("OrderCompleted", order_id))
    assert status(bdb, order_id) == ("HOAN_TAT", 2, None, "KHONG")


@pytest.mark.kb(7)
def test_cancelled_before_reserved_keeps_cancelled(bdb: str) -> None:
    """Scenario 7: Cancelled reaches the branch before Reserved; the branch keeps Cancelled
    and ignores Reserved. The order skips a rank on the way (section 3.1)."""
    order_id = place(bdb)
    cancelled = status_message(
        "OrderCancelled", order_id, {"cancelled_by": "KITCHEN", "reason_code": "SHORT_STAFFED"}
    )
    assert deliver(bdb, cancelled)
    assert status(bdb, order_id) == ("DA_HUY", 2, "SHORT_STAFFED", "KHONG")
    assert deliver(bdb, status_message("OrderReserved", order_id))  # processed, not applied
    assert status(bdb, order_id) == ("DA_HUY", 2, "SHORT_STAFFED", "KHONG")


@pytest.mark.parametrize(
    ("first", "first_payload", "then", "then_payload"),
    [
        ("OrderFailed", {"reason_code": "ORDER_EXPIRED"}, "OrderCancelled", {"reason_code": "X"}),
        ("OrderCompleted", {}, "OrderCancelled", {"reason_code": "CHANGED_MIND"}),
        ("OrderCancelled", {"reason_code": "CHANGED_MIND"}, "OrderCompleted", {}),
        ("OrderCancelled", {"reason_code": "CHANGED_MIND"}, "OrderFailed", {"reason_code": "Y"}),
    ],
)
def test_a_terminal_status_is_never_replaced(
    bdb: str, first: str, first_payload: dict[str, str], then: str, then_payload: dict[str, str]
) -> None:
    """BR3: rank 2 is terminal; another rank-2 message is ignored, reason included."""
    order_id = place(bdb)
    deliver(bdb, status_message(first, order_id, first_payload))
    before = status(bdb, order_id)
    deliver(bdb, status_message(then, order_id, then_payload))
    assert status(bdb, order_id) == before
    assert before[1] == 2


@pytest.mark.kb(8)
def test_failed_turns_the_cancel_flag_off_and_a_late_cancel_pending_is_ignored(bdb: str) -> None:
    """Scenario 8, branch side: the order has a cancel request waiting (the Kitchen holds a
    Cancel-pending record); Inventory's Failed arrives, then the Kitchen's CancelPending,
    which travels through another relay. The branch shows Failed with the flag off."""
    order_id = requested(bdb)
    assert status(bdb, order_id) == ("CHO_KHO", 0, None, "DANG_YEU_CAU")
    deliver(bdb, status_message("OrderFailed", order_id, {"reason_code": "ORDER_EXPIRED"}))
    assert status(bdb, order_id) == ("THAT_BAI", 2, "ORDER_EXPIRED", "KHONG")
    deliver(bdb, status_message("CancelPending", order_id))
    assert status(bdb, order_id) == ("THAT_BAI", 2, "ORDER_EXPIRED", "KHONG")


@pytest.mark.kb(8)
def test_cancel_pending_then_failed(bdb: str) -> None:
    """Scenario 8 in the other order: "kitchen will not cook" first, then Failed."""
    order_id = requested(bdb)
    deliver(bdb, status_message("CancelPending", order_id))
    assert status(bdb, order_id) == ("CHO_KHO", 0, None, "BEP_KHONG_NAU")
    deliver(bdb, status_message("OrderFailed", order_id, {"reason_code": "ORDER_EXPIRED"}))
    assert status(bdb, order_id) == ("THAT_BAI", 2, "ORDER_EXPIRED", "KHONG")


def test_cancel_pending_applies_only_while_a_request_is_waiting(bdb: str) -> None:
    """Write (4): no request waiting (flag ``KHONG``), so CancelPending is ignored."""
    order_id = place(bdb)
    deliver(bdb, status_message("CancelPending", order_id))
    assert status(bdb, order_id) == ("CHO_KHO", 0, None, "KHONG")


@pytest.mark.kb(23)
def test_cancel_rejected_turns_the_flag_off_and_keeps_the_status(bdb: str) -> None:
    """Scenario 23, branch side: the ticket is Cooking, the Kitchen answers CancelRejected.
    The branch shows "Cannot cancel: the kitchen has started cooking"; the status stays."""
    order_id = requested(bdb)
    deliver(bdb, status_message("OrderReserved", order_id))
    deliver(bdb, status_message("CancelRejected", order_id, {"kitchen_status": "DANG_NAU"}))
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["cancel_flag"]) == ("DA_GIU", "KHONG")
    assert row["cancel_message"] == CANCEL_REJECTED_MESSAGE


def test_cancel_rejected_applies_at_any_rank(bdb: str) -> None:
    """Write (5): a CancelRejected for a Completed ticket arrives after OrderCompleted; the
    notice is still recorded."""
    order_id = requested(bdb)
    deliver(bdb, status_message("OrderCompleted", order_id))
    deliver(bdb, status_message("CancelRejected", order_id, {"kitchen_status": "HOAN_TAT"}))
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["cancel_flag"]) == ("HOAN_TAT", "KHONG")
    assert row["cancel_message"] == CANCEL_REJECTED_MESSAGE


def test_a_duplicate_has_no_second_effect(bdb: str) -> None:
    """BR4, both kinds of duplicate: the same ``event_id`` is not processed again; the same
    result in a new message is processed and changes nothing."""
    order_id = place(bdb)
    reserved = status_message("OrderReserved", order_id)
    assert deliver(bdb, reserved)
    deliver(bdb, status_message("OrderCompleted", order_id))
    assert not deliver(bdb, reserved)
    assert deliver(bdb, resent(reserved))
    assert status(bdb, order_id) == ("HOAN_TAT", 2, None, "KHONG")
    assert reserved.event_id in processed(bdb)


def test_a_status_for_an_order_this_branch_does_not_have_changes_nothing(bdb: str) -> None:
    unknown = uuid.uuid4()
    assert deliver(bdb, status_message("OrderReserved", unknown))
    assert order_row(bdb, unknown) is None


def test_a_status_from_another_branch_topic_is_refused(bdb: str) -> None:
    """The handler accepts only this branch's ``status-events``; anything else raises, so the
    consumer treats it as unreadable (5 attempts, the dlq, an alert)."""
    order_id = place(bdb)
    with pytest.raises(ValueError, match="POS02"):
        deliver(bdb, status_message("OrderReserved", order_id), topic="status-events.POS02")
    assert status(bdb, order_id) == ("CHO_KHO", 0, None, "KHONG")
    assert processed(bdb) == set()


def test_a_status_without_order_id_is_refused(bdb: str) -> None:
    with pytest.raises(ValueError, match="order_id"):
        deliver(bdb, status_message("OrderReserved", None))


def test_a_reason_that_is_not_text_is_dropped(bdb: str) -> None:
    order_id = place(bdb)
    deliver(bdb, status_message("OrderFailed", order_id, {"reason_code": 7}))
    assert status(bdb, order_id) == ("THAT_BAI", 2, None, "KHONG")
