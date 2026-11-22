"""Cancelling at the branch (tier 1): the "Branch side" of Flow B, BR5, BR9 and the flag of
section 3.1 of docs/01-business-spec.md; write (2) and ``POST /orders/{id}/cancel`` of
docs/02-detailed-design.md.

The second half hands the branch's real messages to Inventory's and the Kitchen's real handlers
and their answers back to the branch, so the branch side of the Kitchen's scenarios is checked
with the messages those services really send.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Any

import inventory_support as inv
import kitchen_support as kit
import psycopg
import pytest
from branch_support import (
    NOW,
    cancel,
    deliver,
    entries,
    mark_attempted,
    order_row,
    place,
    queued_envelope,
    status_message,
)
from fastapi.testclient import TestClient

from common.clock import FixedClock
from kitchen_service.tickets import complete, reject, start_cooking
from order_service.statuses import CANCEL_REJECTED_MESSAGE


def press_cancel(api: TestClient, order_id: uuid.UUID, reason: str = "CHANGED_MIND") -> Any:
    return api.post(f"/orders/{order_id}/cancel", json={"reason_code": reason})


def flag(bdb: str, order_id: uuid.UUID) -> tuple[str, str]:
    row = order_row(bdb, order_id)
    assert row is not None
    return row["status"], row["cancel_flag"]


# ---------- write (2) through the API ----------


@pytest.mark.kb(10)
def test_an_order_never_attempted_is_cancelled_here_and_its_entry_discarded(
    api: TestClient, bdb: str
) -> None:
    """Scenario 10, branch side: offline, the sender never set the flag; the cashier cancels.
    The branch closes the order as Cancelled at once and discards the entry: nothing will be
    sent. (With the network cut and restored for real: test_branch_e2e.py.)"""
    order_id = place(bdb)
    response = press_cancel(api, order_id, "WRONG_ORDER_ENTERED")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["close_reason"], body["cancel_flag"]) == (
        "DA_HUY",
        "WRONG_ORDER_ENTERED",
        "KHONG",
    )
    assert body["send_state"] is None
    assert entries(bdb) == []


@pytest.mark.parametrize("sent", [False, True], ids=["send-failed", "acknowledged"])
def test_an_attempted_order_goes_to_the_kitchen(api: TestClient, bdb: str, sent: bool) -> None:
    """BR9: once attempted, never cancelled locally, even if that send reported an error. The
    cancel entry queues behind the create-order entry; the flag turns on; the status stays."""
    order_id = place(bdb)
    mark_attempted(bdb, order_id, sent=sent)
    response = press_cancel(api, order_id)
    assert response.status_code == 202, response.text
    body = response.json()
    assert (body["status"], body["cancel_flag"]) == ("CHO_KHO", "DANG_YEU_CAU")
    assert body["cancel_requested_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert body["cancel_send_state"] == "CHUA_GUI"
    assert body["send_state"] == ("DA_GUI" if sent else "DANG_GUI")

    create, cancel_entry = entries(bdb, order_id)
    assert create["kind"] == "TAO_DON" and create["attempted"]
    assert (cancel_entry["kind"], cancel_entry["topic"]) == ("HUY", "cancel-events.POS01")
    assert cancel_entry["id"] > create["id"]
    env = queued_envelope(bdb, order_id, "HUY")
    assert (env.event_type, env.order_id, env.payload) == (
        "CancelRequested",
        order_id,
        {"reason_code": "CHANGED_MIND"},
    )


def test_a_second_press_queues_no_second_request(api: TestClient, bdb: str) -> None:
    order_id = place(bdb)
    mark_attempted(bdb, order_id)
    assert press_cancel(api, order_id).status_code == 202
    assert press_cancel(api, order_id, "WAITED_TOO_LONG").status_code == 202
    deliver(bdb, status_message("CancelPending", order_id))
    assert press_cancel(api, order_id).status_code == 202
    assert [e["kind"] for e in entries(bdb, order_id)] == ["TAO_DON", "HUY"]
    assert flag(bdb, order_id) == ("CHO_KHO", "BEP_KHONG_NAU")


def test_after_a_refusal_the_cashier_can_ask_again(api: TestClient, bdb: str) -> None:
    """The flag is off after CancelRejected; a new press queues a new request and clears the
    old notice."""
    order_id = place(bdb)
    mark_attempted(bdb, order_id, sent=True)
    press_cancel(api, order_id)
    deliver(bdb, status_message("CancelRejected", order_id, {"kitchen_status": "DANG_NAU"}))
    response = press_cancel(api, order_id)
    assert response.status_code == 202
    assert response.json()["cancel_message"] is None
    assert [e["kind"] for e in entries(bdb, order_id)] == ["TAO_DON", "HUY", "HUY"]


def test_a_terminal_order_cannot_be_cancelled(api: TestClient, bdb: str) -> None:
    order_id = place(bdb)
    deliver(bdb, status_message("OrderCompleted", order_id))
    response = press_cancel(api, order_id)
    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "HOAN_TAT"
    assert [e["kind"] for e in entries(bdb, order_id)] == ["TAO_DON"]


@pytest.mark.parametrize("reason", ["SHORT_STAFFED", "ANYTHING", ""])
def test_the_reason_must_be_a_customer_cancel_reason(
    api: TestClient, bdb: str, reason: str
) -> None:
    order_id = place(bdb)
    assert press_cancel(api, order_id, reason).status_code == 400
    assert api.post(f"/orders/{order_id}/cancel", json={}).status_code == 400
    assert flag(bdb, order_id) == ("CHO_KHO", "KHONG")
    assert len(entries(bdb, order_id)) == 1


def test_an_unknown_order_is_404(api: TestClient) -> None:
    assert press_cancel(api, uuid.uuid4()).status_code == 404


# ---------- through the real Inventory and Kitchen handlers ----------


def answers(dsn: str, event_type: str, order_id: uuid.UUID) -> list[Any]:
    """What Inventory or the Kitchen sent to ``status-events.POS01`` for the order."""
    return [
        e
        for e in kit.sent_envelopes(dsn, event_type, "status-events.POS01")
        if e.order_id == order_id
    ]


def relay(dsn: str, bdb: str, event_type: str, order_id: uuid.UUID) -> None:
    """Deliver the service's latest answer of that type to the branch."""
    found = answers(dsn, event_type, order_id)
    assert found, f"no {event_type} for {order_id}"
    assert deliver(bdb, found[-1])


@pytest.fixture
def sides(migrated: Callable[[str], str]) -> Iterator[tuple[str, str]]:
    """(Inventory DB with the seed stock, Kitchen DB). Inventory's two invariants are checked
    after each test."""
    idb = inv.seeded(migrated("inventory-service"))
    yield idb, migrated("kitchen-service")
    inv.assert_invariants(idb)


def to_inventory(kdb: str, idb: str, order_id: uuid.UUID) -> str | None:
    """Hand the Kitchen's commands for the order to Inventory's real handler; returns the
    status of Inventory's record afterwards."""
    for event_type in ("ReleaseRequested", "StockConsumed"):
        for env in kit.sent_envelopes(kdb, event_type, "stock-commands"):
            if env.order_id == order_id:
                inv.deliver(idb, env)
    record = inv.order_record(idb, order_id)
    return None if record is None else record[0]


def sent_order(bdb: str) -> uuid.UUID:
    """An order the sender has attempted and Kafka has acknowledged."""
    order_id = place(bdb)
    mark_attempted(bdb, order_id, sent=True)
    return order_id


def kitchen_button(kdb: str, action: Callable[[psycopg.Connection[Any]], Any]) -> None:
    with psycopg.connect(kdb) as conn:
        action(conn)
        conn.commit()


@pytest.mark.kb(1)
def test_cancel_before_the_order_reaches_the_kitchen(bdb: str, sides: tuple[str, str]) -> None:
    """The cancel request overtakes the order (scenario 1): the branch first shows "kitchen
    will not cook", then Cancelled; Inventory's late Reserved does not move it back."""
    idb, kdb = sides
    order_id = sent_order(bdb)
    assert cancel(bdb, order_id) is False
    kit.deliver(kdb, queued_envelope(bdb, order_id, "HUY"))
    relay(kdb, bdb, "CancelPending", order_id)
    assert flag(bdb, order_id) == ("CHO_KHO", "BEP_KHONG_NAU")

    kit.deliver(kdb, kit.through_inventory(idb, queued_envelope(bdb, order_id)))
    relay(kdb, bdb, "OrderCancelled", order_id)
    assert flag(bdb, order_id) == ("DA_HUY", "KHONG")
    relay(idb, bdb, "OrderReserved", order_id)
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["close_reason"]) == ("DA_HUY", "CHANGED_MIND")
    assert to_inventory(kdb, idb, order_id) == "DA_TRA"


@pytest.mark.kb(3)
@pytest.mark.parametrize("winner", ["cancel", "cooking"])
def test_cancel_and_start_cooking_agree_at_the_branch(
    bdb: str, sides: tuple[str, str], winner: str
) -> None:
    """Scenario 3, branch side, for each winner the Kitchen can record (the race itself is
    test_cancel_race.py at the Kitchen): the branch, the Kitchen and Inventory all end in the
    winner's status."""
    idb, kdb = sides
    order_id = sent_order(bdb)
    kit.deliver(kdb, kit.through_inventory(idb, queued_envelope(bdb, order_id)))
    relay(idb, bdb, "OrderReserved", order_id)
    assert cancel(bdb, order_id) is False
    if winner == "cooking":
        kitchen_button(kdb, lambda c: start_cooking(c, order_id, FixedClock(NOW)))
    kit.deliver(kdb, queued_envelope(bdb, order_id, "HUY"))

    if winner == "cancel":
        relay(kdb, bdb, "OrderCancelled", order_id)
        assert flag(bdb, order_id) == ("DA_HUY", "KHONG")
    else:
        relay(kdb, bdb, "CancelRejected", order_id)
        assert flag(bdb, order_id) == ("DA_GIU", "KHONG")
        kitchen_button(kdb, lambda c: complete(c, order_id, FixedClock(NOW)))
        relay(kdb, bdb, "OrderCompleted", order_id)
        assert flag(bdb, order_id) == ("HOAN_TAT", "KHONG")
    ticket = kit.record(kdb, order_id)
    assert ticket is not None
    assert ticket["status"] == ("DA_HUY" if winner == "cancel" else "HOAN_TAT")
    # Inventory agrees: released for the cancel, consumed for cooking.
    assert to_inventory(kdb, idb, order_id) == ("DA_TRA" if winner == "cancel" else "DA_DUNG")


@pytest.mark.kb(23)
def test_a_cancel_reaching_a_cooking_ticket_is_refused_at_the_branch(
    bdb: str, sides: tuple[str, str]
) -> None:
    idb, kdb = sides
    order_id = sent_order(bdb)
    kit.deliver(kdb, kit.through_inventory(idb, queued_envelope(bdb, order_id)))
    relay(idb, bdb, "OrderReserved", order_id)
    kitchen_button(kdb, lambda c: start_cooking(c, order_id, FixedClock(NOW)))
    cancel(bdb, order_id)
    kit.deliver(kdb, queued_envelope(bdb, order_id, "HUY"))
    relay(kdb, bdb, "CancelRejected", order_id)
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["cancel_flag"]) == ("DA_GIU", "KHONG")
    assert row["cancel_message"] == CANCEL_REJECTED_MESSAGE


@pytest.mark.kb(4)
def test_a_kitchen_rejection_shows_cancelled_at_once(bdb: str, sides: tuple[str, str]) -> None:
    """Scenario 4, branch side: the Kitchen's Cancelled reaches the branch without Inventory."""
    idb, kdb = sides
    order_id = sent_order(bdb)
    kit.deliver(kdb, kit.through_inventory(idb, queued_envelope(bdb, order_id)))
    kitchen_button(kdb, lambda c: reject(c, order_id, "EQUIPMENT_FAILURE", [], FixedClock(NOW)))
    relay(kdb, bdb, "OrderCancelled", order_id)
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["close_reason"]) == ("DA_HUY", "EQUIPMENT_FAILURE")


@pytest.mark.kb(8)
def test_a_cancel_pending_order_failed_by_inventory(bdb: str, sides: tuple[str, str]) -> None:
    """Scenario 8 with the real messages: the Kitchen holds Cancel-pending, Inventory fails the
    order (it arrives after X hours); the branch shows Failed with the flag off, also when the
    Kitchen's CancelPending arrives after Inventory's Failed (the other order:
    test_statuses.py)."""
    idb, kdb = sides
    order_id = sent_order(bdb)
    cancel(bdb, order_id)
    kit.deliver(kdb, queued_envelope(bdb, order_id, "HUY"))
    inv.deliver(idb, queued_envelope(bdb, order_id), clock=FixedClock(NOW + timedelta(hours=5)))
    [to_kitchen] = kit.sent_envelopes(idb, "OrderFailed", "kitchen-orders")
    kit.deliver(kdb, to_kitchen)

    relay(idb, bdb, "OrderFailed", order_id)
    relay(kdb, bdb, "CancelPending", order_id)
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["close_reason"], row["cancel_flag"]) == (
        "THAT_BAI",
        "ORDER_EXPIRED",
        "KHONG",
    )
    ticket = kit.record(kdb, order_id)
    assert ticket is not None and ticket["status"] == "THAT_BAI"


@pytest.mark.kb(33)
def test_a_cancel_after_inventory_failed_gets_failed_back(bdb: str, sides: tuple[str, str]) -> None:
    """Scenario 33, branch side: Inventory's Failed reached the Kitchen first; the branch's
    later cancel request gets the stored result, Failed, and the flag turns off."""
    idb, kdb = sides
    order_id = sent_order(bdb)
    inv.set_available(idb, "THIT_BO", inv.D("0"))
    kit.deliver(kdb, kit.through_inventory(idb, queued_envelope(bdb, order_id)))
    cancel(bdb, order_id)
    kit.deliver(kdb, queued_envelope(bdb, order_id, "HUY"))
    relay(kdb, bdb, "OrderFailed", order_id)  # the Kitchen's stored result
    row = order_row(bdb, order_id)
    assert row is not None
    assert (row["status"], row["close_reason"], row["cancel_flag"]) == (
        "THAT_BAI",
        "INSUFFICIENT_INGREDIENTS",
        "KHONG",
    )
    assert answers(kdb, "CancelPending", order_id) == []
    ticket = kit.record(kdb, order_id)
    assert ticket is not None and ticket["status"] == "THAT_BAI"  # no Cancel-pending record
