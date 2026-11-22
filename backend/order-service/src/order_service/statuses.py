"""The branch applies the status messages of its own ``status-events.<branch>``.

Section 3.1 of docs/01-business-spec.md (ranks, the "Cancel requested" flag) and BR3; the table
"The branch applies status messages as follows" in section 2 and writes (3), (4), (5) of
section 5 of docs/02-detailed-design.md, used as they are:

- (3) a status moves forward only, ``WHERE status_rank < :rank``; a terminal status turns the
  flag off and is never replaced. Reserved arriving after Cancelled is ignored (scenario 7).
- (4) ``CancelPending`` applies only while the order is not terminal and the flag is
  ``DANG_YEU_CAU``: it can arrive after Inventory's Failed, which travels another way
  (scenario 8).
- (5) ``CancelRejected`` turns the flag off and records the notice at any rank (scenarios 23,
  36).

The branch is a display-only side (section 9): a message it cannot apply is never an error.
"""

import logging
import uuid
from typing import Any, Final

import psycopg

from common.consumer import Handler, Incoming
from common.envelope import Envelope
from order_service.orders import (
    CANCELLED,
    COMPLETED,
    FAILED,
    FLAG_OFF,
    FLAG_REQUESTED,
    FLAG_WILL_NOT_COOK,
    RANK,
    RESERVED,
    TERMINAL_RANK,
)

log = logging.getLogger(__name__)

STATUS_OF: Final = {
    "OrderReserved": RESERVED,
    "OrderFailed": FAILED,
    "OrderCancelled": CANCELLED,
    "OrderCompleted": COMPLETED,
}
CANCEL_REJECTED_MESSAGE: Final = "Cannot cancel: the kitchen has started cooking"
"""The notice stored in ``cancel_message`` (section 3.1); the screens show it in Vietnamese."""


def branch_handlers(branch: str) -> dict[str, Handler]:
    """event_type -> handler for the messages a branch receives on ``status-events.<branch>``.
    ``DishStatusChanged`` and ``Heartbeat`` (``menu-events``) come with phase 2."""
    status = _status_handler(branch)
    return {
        **dict.fromkeys(STATUS_OF, status),
        "CancelPending": _cancel_pending_handler(branch),
        "CancelRejected": _cancel_rejected_handler(branch),
    }


def _order_id(message: Incoming, branch: str) -> uuid.UUID:
    env = message.envelope
    # The consumer reads only this branch's status topic; a message from anywhere else is a
    # wiring fault, treated as unreadable (5 attempts, the dlq, an alert).
    if message.source_branch != branch:
        raise ValueError(f"{env.event_type} arrived from {message.source_branch}, not {branch}")
    if env.order_id is None:
        raise ValueError(f"{env.event_type} has no order_id")
    return env.order_id


def _reason(env: Envelope) -> str | None:
    if env.event_type not in ("OrderFailed", "OrderCancelled"):
        return None
    reason = env.payload.get("reason_code")
    if reason is None or isinstance(reason, str):
        return reason
    log.warning("order_id=%s %s: reason_code %r ignored", env.order_id, env.event_type, reason)
    return None


def _status_handler(branch: str) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        order_id = _order_id(message, branch)
        status = STATUS_OF[env.event_type]
        rank = RANK[status]
        # Write (3) of section 5 of document 02.
        updated = conn.execute(
            """
            UPDATE orders SET status = %s, status_rank = %s,
                   close_reason = COALESCE(%s, close_reason),
                   cancel_flag = CASE WHEN %s = 2 THEN 'KHONG' ELSE cancel_flag END
             WHERE order_id = %s AND status_rank < %s
            """,
            (status, rank, _reason(env), rank, order_id, rank),
        ).rowcount
        if updated:
            log.info("order_id=%s -> %s", order_id, status)
        else:
            _not_applied(conn, env, order_id)

    return handle


def _cancel_pending_handler(branch: str) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        order_id = _order_id(message, branch)
        # Write (4).
        updated = conn.execute(
            "UPDATE orders SET cancel_flag = %s"
            " WHERE order_id = %s AND status_rank < %s AND cancel_flag = %s",
            (FLAG_WILL_NOT_COOK, order_id, TERMINAL_RANK, FLAG_REQUESTED),
        ).rowcount
        if updated:
            log.info("order_id=%s cancel requested: kitchen will not cook", order_id)
        else:
            _not_applied(conn, env, order_id)

    return handle


def _cancel_rejected_handler(branch: str) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        order_id = _order_id(message, branch)
        # Write (5).
        updated = conn.execute(
            "UPDATE orders SET cancel_flag = %s, cancel_message = %s WHERE order_id = %s",
            (FLAG_OFF, CANCEL_REJECTED_MESSAGE, order_id),
        ).rowcount
        if updated:
            log.info("order_id=%s cancel rejected: the kitchen has started cooking", order_id)
        else:
            _not_applied(conn, env, order_id)

    return handle


def _not_applied(conn: psycopg.Connection[Any], env: Envelope, order_id: uuid.UUID) -> None:
    row = conn.execute(
        "SELECT status, cancel_flag FROM orders WHERE order_id = %s", (order_id,)
    ).fetchone()
    if row is None:
        log.warning(
            "order_id=%s %s for an order this branch does not have", order_id, env.event_type
        )
    else:
        log.info(
            "order_id=%s %s ignored: status %s, flag %s", order_id, env.event_type, row[0], row[1]
        )
