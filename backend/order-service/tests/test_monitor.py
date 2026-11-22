"""Flow D at the branch (tier 1): the branch rows of section 8 of docs/01-business-spec.md and
the parameters of section 10, through ``GET /monitor``."""

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any

import psycopg
import pytest
from branch_support import NOW, cancel, mark_attempted, order_row, place, status_message
from branch_support import deliver as deliver_status
from fastapi.testclient import TestClient

from common.alerts import NEEDS_REVIEW, write_alert
from common.clock import FixedClock
from order_service.app import app, get_connection_status
from order_service.orders import cancel_order
from order_service.sender import ConnectionStatus


@pytest.fixture
def offline(api: TestClient) -> Iterator[TestClient]:
    """The sender's most recent probe failed one second ago."""
    app.dependency_overrides[get_connection_status] = lambda: ConnectionStatus(
        False, NOW - timedelta(seconds=1)
    )
    yield api


def monitor(api: TestClient) -> dict[str, Any]:
    response = api.get("/monitor")
    assert response.status_code == 200, response.text
    return response.json()


def _iso(at: datetime) -> str:
    return at.isoformat().replace("+00:00", "Z")


def ago(**kwargs: float) -> FixedClock:
    return FixedClock(NOW - timedelta(**kwargs))


@pytest.mark.kb(53)
def test_an_order_awaiting_inventory_too_long_raises_an_alert_with_a_cancel_button(
    api: TestClient, bdb: str
) -> None:
    """Scenario 53: Inventory is down, an order stays in Awaiting Inventory for more than
    N = 10 minutes. The branch shows the alert; the order does not change status by itself;
    the alert's Request cancellation button is the ordinary cancel."""
    waiting = place(bdb, clock=ago(minutes=11))
    mark_attempted(bdb, waiting, sent=True)  # Kafka has it; Inventory does not answer
    recent = place(bdb, clock=ago(minutes=9))
    answered = place(bdb, clock=ago(minutes=30))
    deliver_status(bdb, status_message("OrderReserved", answered))

    alerts = monitor(api)["awaiting_inventory"]
    assert [a["order_id"] for a in alerts] == [str(waiting)]
    assert alerts[0]["waited_s"] == 11 * 60
    for order_id in (waiting, recent):  # no status changes by itself (Q6)
        row = order_row(bdb, order_id)
        assert row is not None and row["status"] == "CHO_KHO"

    response = api.post(f"/orders/{waiting}/cancel", json={"reason_code": "WAITED_TOO_LONG"})
    assert response.status_code == 202
    [alert] = monitor(api)["awaiting_inventory"]
    assert alert["cancel_flag"] == "DANG_YEU_CAU"  # still waiting: the Kitchen decides


@pytest.mark.kb(54)
def test_offline_the_branch_shows_the_connection_the_queue_and_orders_about_to_expire(
    offline: TestClient, bdb: str
) -> None:
    """Scenario 54: POS is offline; an order in the send queue is less than 1 hour away from
    the X = 4 hour limit. The branch shows the lost connection, the number of entries waiting
    to be sent and the alert that the order is about to expire."""
    expiring = place(bdb, clock=ago(hours=3, minutes=5))
    expired = place(bdb, clock=ago(hours=4, minutes=1))
    place(bdb, clock=ago(hours=2, minutes=50))  # more than an hour left
    sent = place(bdb, clock=ago(hours=3, minutes=30))
    mark_attempted(bdb, sent, sent=True)  # already in Kafka: not in the send queue
    attempted = place(bdb, clock=ago(hours=3, minutes=10))
    mark_attempted(bdb, attempted)  # attempted, not acknowledged: still in the queue
    answered = place(bdb, clock=ago(hours=3, minutes=20))
    mark_attempted(bdb, answered)  # Kafka has it although its acknowledgement was lost:
    deliver_status(bdb, status_message("OrderReserved", answered))  # Inventory answered

    body = monitor(offline)
    assert body["connection"] == {
        "connected": False,
        "checked_at": _iso(NOW - timedelta(seconds=1)),
    }
    assert body["waiting_to_send"] == 5  # entries without Kafka's acknowledgement
    assert {a["order_id"]: a["expires_at"] for a in body["about_to_expire"]} == {
        str(expired): _iso(NOW - timedelta(minutes=1)),
        str(attempted): _iso(NOW + timedelta(minutes=50)),
        str(expiring): _iso(NOW + timedelta(minutes=55)),
    }


def test_orders_with_the_cancel_flag_show_the_time_waited(api: TestClient, bdb: str) -> None:
    """Section 6, "Kitchen down": the flag is shown with the time waited so far."""
    order_id = place(bdb)
    mark_attempted(bdb, order_id, sent=True)
    with psycopg.connect(bdb) as conn:
        cancel_order(conn, "POS01", order_id, "CHANGED_MIND", ago(minutes=7))
        conn.commit()
    other = place(bdb)
    mark_attempted(bdb, other, sent=True)
    cancel(bdb, other)
    deliver_status(bdb, status_message("CancelPending", other))

    flagged = {a["order_id"]: a for a in monitor(api)["cancel_requested"]}
    assert flagged[str(order_id)]["cancel_flag"] == "DANG_YEU_CAU"
    assert flagged[str(order_id)]["waited_s"] == 7 * 60
    assert flagged[str(other)]["cancel_flag"] == "BEP_KHONG_NAU"


def test_message_alerts_are_listed(api: TestClient, bdb: str) -> None:
    """Section 9: the branch's "raise an alert" for a message it could not read or did not
    recognise is an ``alerts`` row (revision 14 of document 02), shown here."""
    order_id = uuid.uuid4()
    with psycopg.connect(bdb) as conn:
        for offset in (5, 6):
            write_alert(
                conn,
                NEEDS_REVIEW,
                order_id=order_id,
                event_id=None,
                source_topic="status-events.POS01",
                source_partition=0,
                source_offset=offset,
                detail={"error": "unknown event_type 'X'"},
            )
        conn.commit()
    alerts = monitor(api)["message_alerts"]
    assert alerts["count"] == 2
    assert [a["kind"] for a in alerts["latest"]] == ["CAN_KIEM_TRA", "CAN_KIEM_TRA"]
    assert alerts["latest"][0]["detail"] == {"error": "unknown event_type 'X'"}


def test_a_new_branch_monitor_is_empty_and_the_connection_unknown(api: TestClient) -> None:
    body = monitor(api)
    assert body == {
        "connection": {"connected": None, "checked_at": None},
        "waiting_to_send": 0,
        "awaiting_inventory": [],
        "about_to_expire": [],
        "cancel_requested": [],
        "message_alerts": {"count": 0, "latest": []},
    }
