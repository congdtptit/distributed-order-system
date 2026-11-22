"""Flow D at a branch: ``GET /monitor``.

The branch rows of the table in section 8 of docs/01-business-spec.md, with the parameters of
section 10, and the branch's message alerts (section 9; the ``alerts`` table of section 5 of
docs/02-detailed-design.md). Nothing here changes an order: the system only raises alerts
and never cancels an order because it has waited long (Q6).
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import psycopg

from common.clock import Clock
from order_service.orders import AWAITING, CREATE_ENTRY, FLAG_OFF
from order_service.sender import ConnectionStatus

LATEST_ALERTS = 20


@dataclass(frozen=True)
class MonitorLimits:
    """Section 10 of the specification (proposed values)."""

    awaiting_alert: timedelta = timedelta(minutes=10)
    """N: alert for an order in Awaiting Inventory for longer than this (scenario 53)."""
    expiry: timedelta = timedelta(hours=4)
    """X: Inventory fails an order created longer ago than this (BR11)."""
    expiry_warning: timedelta = timedelta(hours=1)
    """Alert for an order still in the send queue less than this before X (scenario 54)."""


def monitor_view(
    conn: psycopg.Connection[Any],
    connection: ConnectionStatus,
    clock: Clock,
    limits: MonitorLimits,
) -> dict[str, Any]:
    now = clock.now()
    waiting = conn.execute("SELECT count(*) FROM outbox_events WHERE sent_at IS NULL").fetchone()
    awaiting = conn.execute(
        """
        SELECT order_id, created_at, cancel_flag FROM orders
         WHERE status = %s AND created_at <= %s
         ORDER BY created_at, order_id
        """,
        (AWAITING, now - limits.awaiting_alert),
    ).fetchall()
    expiring = conn.execute(
        """
        SELECT o.order_id, o.created_at FROM orders o
         WHERE EXISTS (SELECT 1 FROM outbox_events e
                        WHERE e.order_id = o.order_id AND e.kind = %s AND e.sent_at IS NULL)
           AND o.status_rank = 0
           AND o.created_at <= %s
         ORDER BY o.created_at, o.order_id
        """,
        (CREATE_ENTRY, now - (limits.expiry - limits.expiry_warning)),
    ).fetchall()
    flagged = conn.execute(
        """
        SELECT order_id, cancel_flag, cancel_requested_at FROM orders
         WHERE cancel_flag <> %s
         ORDER BY cancel_requested_at, order_id
        """,
        (FLAG_OFF,),
    ).fetchall()
    alert_count = conn.execute("SELECT count(*) FROM alerts").fetchone()
    latest = conn.execute(
        """
        SELECT kind, order_id, event_id, source_topic, detail, created_at FROM alerts
         ORDER BY id DESC LIMIT %s
        """,
        (LATEST_ALERTS,),
    ).fetchall()
    assert waiting is not None and alert_count is not None
    return {
        "connection": {"connected": connection.connected, "checked_at": connection.checked_at},
        "waiting_to_send": int(waiting[0]),
        "awaiting_inventory": [
            {
                "order_id": r[0],
                "created_at": r[1],
                "waited_s": int((now - r[1]).total_seconds()),
                "cancel_flag": r[2],
            }
            for r in awaiting
        ],
        "about_to_expire": [
            {"order_id": r[0], "created_at": r[1], "expires_at": r[1] + limits.expiry}
            for r in expiring
        ],
        "cancel_requested": [
            {
                "order_id": r[0],
                "cancel_flag": r[1],
                "cancel_requested_at": r[2],
                "waited_s": None if r[2] is None else int((now - r[2]).total_seconds()),
            }
            for r in flagged
        ],
        "message_alerts": {
            "count": int(alert_count[0]),
            "latest": [
                {
                    "kind": r[0],
                    "order_id": r[1],
                    "event_id": r[2],
                    "source_topic": r[3],
                    "detail": r[4],
                    "created_at": r[5],
                }
                for r in latest
            ],
        },
    }
