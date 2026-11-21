"""The Kitchen's order record: table 3.2 of docs/01-business-spec.md, BR2, BR7, BR8, Flow A;
section 4 of docs/02-detailed-design.md.

One entry point for every change (section 13.4): insert a ``CHUA_CO`` row if none exists,
``SELECT ... FOR UPDATE``, apply table 3.2, write the outbox, commit. Inventory's messages and
the three staff buttons all go through ``_lock``; every transition is a conditional write on
the status just read under the row lock.

Step 4 covers the main path: Inventory's ``OrderReserved`` and ``OrderFailed``, Start cooking,
Reject, Complete, and the stock-check flags. Cancel requests (``HUY_CHO_DON``) are step 5; the
rows of table 3.2 where Inventory's messages meet a Cancel-pending record are already here.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from common import reasons
from common.alerts import WRONG_BRANCH_CANCEL, write_alert
from common.clock import Clock
from common.consumer import Handler, Incoming
from common.envelope import Envelope, new_envelope
from common.outbox import enqueue
from common.topics import STOCK_COMMANDS, status_events

log = logging.getLogger(__name__)

NONE, CANCEL_PENDING, QUEUED, COOKING = "CHUA_CO", "HUY_CHO_DON", "CHO_NAU", "DANG_NAU"
COMPLETED, CANCELLED, FAILED = "HOAN_TAT", "DA_HUY", "THAT_BAI"
TERMINAL = frozenset({COMPLETED, CANCELLED, FAILED})
CUSTOMER, KITCHEN = "CUSTOMER", "KITCHEN"

_COLUMNS = (
    "order_id, status, origin_branch, cancel_branches, cancel_reasons, cancelled_by,"
    " close_reason, items, reserved, spoiled, order_created_at"
)


@dataclass
class Record:
    order_id: uuid.UUID
    status: str
    origin_branch: str | None
    cancel_branches: list[str]
    cancel_reasons: dict[str, str]
    cancelled_by: str | None
    close_reason: str | None
    items: list[dict[str, Any]] | None
    reserved: list[dict[str, Any]] | None
    spoiled: list[str] | None
    order_created_at: datetime | None
    warnings: list[str] = field(default_factory=lambda: [])


class ActionError(Exception):
    """A staff button that cannot run: 404 (no ticket), 409 (wrong status), 400 (bad input)."""

    def __init__(self, status_code: int, message: str, current: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.current = current


def _record(row: tuple[Any, ...]) -> Record:
    return Record(
        order_id=row[0],
        status=str(row[1]),
        origin_branch=row[2],
        cancel_branches=list(row[3]),
        cancel_reasons=dict(row[4]),
        cancelled_by=row[5],
        close_reason=row[6],
        items=row[7],
        reserved=row[8],
        spoiled=row[9],
        order_created_at=row[10],
    )


def _lock(conn: psycopg.Connection[Any], order_id: uuid.UUID, *, create: bool) -> Record | None:
    """The row-lock sequence of section 13.4. ``create`` inserts the ``CHUA_CO`` placeholder
    (messages); the buttons do not create rows for unknown orders."""
    if create:
        conn.execute(
            "INSERT INTO kitchen_orders (order_id, status) VALUES (%s, %s)"
            " ON CONFLICT (order_id) DO NOTHING",
            (order_id, NONE),
        )
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM kitchen_orders WHERE order_id = %s FOR UPDATE",  # pyright: ignore[reportArgumentType]
        (order_id,),
    ).fetchone()
    return None if row is None else _record(row)


def _set(
    conn: psycopg.Connection[Any], rec: Record, expected: str, clock: Clock, **values: Any
) -> None:
    """A conditional write on the status read under the lock (BR7)."""
    columns = ", ".join(f"{name} = %s" for name in values)
    params = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in values.values()]
    changed = conn.execute(
        f"UPDATE kitchen_orders SET {columns}, updated_at = %s"  # pyright: ignore[reportArgumentType]
        " WHERE order_id = %s AND status = %s",
        (*params, clock.now(), rec.order_id, expected),
    ).rowcount
    if changed != 1:
        raise RuntimeError(f"order {rec.order_id} left {expected} while locked")


def _emit(
    conn: psycopg.Connection[Any],
    topic: str,
    event_type: str,
    rec: Record,
    clock: Clock,
    payload: dict[str, Any],
    cause: Envelope | None = None,
) -> None:
    enqueue(
        conn,
        topic,
        new_envelope(
            event_type,
            order_id=rec.order_id,
            branch_id=rec.origin_branch,
            clock=clock,
            payload=payload,
            causation_id=None if cause is None else cause.event_id,
        ),
    )


def _release(
    conn: psycopg.Connection[Any],
    rec: Record,
    clock: Clock,
    *,
    cancelled_by: str,
    reason: str,
    spoiled: list[str],
    cause: Envelope | None = None,
) -> None:
    """Cancelled: the release command to Inventory and the result to the origin branch, in the
    same transaction as the status change (stored durably before it is sent, scenario 4)."""
    assert rec.origin_branch is not None
    _emit(
        conn,
        STOCK_COMMANDS,
        "ReleaseRequested",
        rec,
        clock,
        {"cancelled_by": cancelled_by, "reason_code": reason, "spoiled_ingredients": spoiled},
        cause,
    )
    _emit(
        conn,
        status_events(rec.origin_branch),
        "OrderCancelled",
        rec,
        clock,
        {"cancelled_by": cancelled_by, "reason_code": reason},
        cause,
    )


def _stored_result(
    conn: psycopg.Connection[Any], rec: Record, clock: Clock, cause: Envelope
) -> None:
    """The last row of table 3.2: a repeat reaching a terminal status gets the stored result
    again, to the origin branch, and never a second release command (section 2 of document 02)."""
    if rec.origin_branch is None:
        return
    topic = status_events(rec.origin_branch)
    if rec.status == CANCELLED:
        payload = {"cancelled_by": rec.cancelled_by, "reason_code": rec.close_reason}
        _emit(conn, topic, "OrderCancelled", rec, clock, payload, cause)
    elif rec.status == FAILED:
        payload = {"origin_branch": rec.origin_branch, "reason_code": rec.close_reason}
        _emit(conn, topic, "OrderFailed", rec, clock, payload, cause)
    elif rec.status == COMPLETED:
        _emit(conn, topic, "OrderCompleted", rec, clock, {}, cause)


# ---------- Inventory's messages on kitchen-orders ----------


def make_order_reserved_handler(clock: Clock) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        order_id = _order_id(env)
        payload = env.payload
        origin = payload.get("origin_branch")
        if not isinstance(origin, str) or not origin:
            raise ValueError("OrderReserved without origin_branch")
        rec = _lock(conn, order_id, create=True)
        assert rec is not None
        ticket: dict[str, Any] = {
            "origin_branch": origin,
            "items": payload.get("items"),
            "reserved": payload.get("reserved"),
            "order_created_at": _time(payload.get("created_at")),
        }

        if rec.status == NONE:
            _set(conn, rec, NONE, clock, status=QUEUED, **ticket)
            log.info("order_id=%s event_id=%s ticket queued", order_id, env.event_id)
        elif rec.status == CANCEL_PENDING:
            rec.origin_branch = origin
            if origin in rec.cancel_branches:
                reason = rec.cancel_reasons.get(origin, reasons.CHANGED_MIND)
                _set(
                    conn,
                    rec,
                    CANCEL_PENDING,
                    clock,
                    status=CANCELLED,
                    cancelled_by=CUSTOMER,
                    close_reason=reason,
                    **ticket,
                )
                _release(
                    conn, rec, clock, cancelled_by=CUSTOMER, reason=reason, spoiled=[], cause=env
                )
                log.info("order_id=%s event_id=%s cancelled on arrival", order_id, env.event_id)
            else:
                dismissed = list(rec.cancel_branches)
                _set(
                    conn,
                    rec,
                    CANCEL_PENDING,
                    clock,
                    status=QUEUED,
                    cancel_branches=[],
                    cancel_reasons={},
                    **ticket,
                )
                _wrong_branch_alert(conn, message, origin, dismissed)
                log.warning(
                    "order_id=%s event_id=%s cancel requests from %s dismissed: origin is %s",
                    order_id,
                    env.event_id,
                    ", ".join(dismissed),
                    origin,
                )
        elif rec.status in (QUEUED, COOKING):
            log.info("order_id=%s event_id=%s duplicate order ignored", order_id, env.event_id)
        else:
            _stored_result(conn, rec, clock, env)

    return handle


def make_order_failed_handler(clock: Clock) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        order_id = _order_id(env)
        origin = env.payload.get("origin_branch")
        reason = env.payload.get("reason_code")
        rec = _lock(conn, order_id, create=True)
        assert rec is not None
        if rec.status in (NONE, CANCEL_PENDING):
            # Record the final result (BR8, prohibition 11), so that a later cancel request does
            # not create a Cancel-pending record.
            _set(
                conn,
                rec,
                rec.status,
                clock,
                status=FAILED,
                origin_branch=origin if isinstance(origin, str) else None,
                close_reason=reason if isinstance(reason, str) else None,
            )
            log.info(
                "order_id=%s event_id=%s failed at Inventory: %s", order_id, env.event_id, reason
            )
        elif rec.status in TERMINAL:
            _stored_result(conn, rec, clock, env)
        else:
            # Queued or Cooking: table 3.2 has no such row (Inventory keeps one result per
            # order, BR12), so the message changes nothing.
            log.warning(
                "order_id=%s event_id=%s OrderFailed for a %s ticket ignored: not in table 3.2",
                order_id,
                env.event_id,
                rec.status,
            )

    return handle


# ---------- flags from Inventory on menu-events ----------


def make_check_changed_handler() -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        p = message.envelope.payload
        ingredient_id, needs_check, epoch, seq = (
            p.get("ingredient_id"),
            p.get("needs_check"),
            p.get("epoch"),
            p.get("seq"),
        )
        if not (
            isinstance(ingredient_id, str)
            and isinstance(needs_check, bool)
            and isinstance(epoch, int)
            and isinstance(seq, int)
        ):
            raise ValueError(f"IngredientCheckChanged with a malformed payload: {p}")
        # Overwritten only by a greater (epoch, seq): messages may arrive out of order.
        conn.execute(
            """
            INSERT INTO flagged_ingredients (ingredient_id, needs_check, epoch, seq)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ingredient_id) DO UPDATE
               SET needs_check = EXCLUDED.needs_check, epoch = EXCLUDED.epoch, seq = EXCLUDED.seq
             WHERE (flagged_ingredients.epoch, flagged_ingredients.seq)
                 < (EXCLUDED.epoch, EXCLUDED.seq)
            """,
            (ingredient_id, needs_check, epoch, seq),
        )

    return handle


# ---------- the three staff buttons (section 6 of document 02) ----------


def start_cooking(conn: psycopg.Connection[Any], order_id: uuid.UUID, clock: Clock) -> Record:
    """Queued → Cooking; reports Consumed to Inventory."""
    rec = _ticket(conn, order_id, QUEUED)
    _set(conn, rec, QUEUED, clock, status=COOKING)
    _emit(conn, STOCK_COMMANDS, "StockConsumed", rec, clock, {})
    rec.status = COOKING
    log.info("order_id=%s cooking", order_id)
    return rec


def reject(
    conn: psycopg.Connection[Any],
    order_id: uuid.UUID,
    reason: str,
    spoiled: list[str],
    clock: Clock,
) -> Record:
    """Queued → Cancelled (Kitchen rejection), Flow A; the release command carries the reason
    and the spoiled ingredients (BR6)."""
    if reason not in reasons.KITCHEN_REJECTION:
        raise ActionError(400, f"{reason} is not a Kitchen rejection reason")
    rec = _ticket(conn, order_id, QUEUED)
    on_ticket = {str(r.get("ingredient_id")) for r in rec.reserved or []}
    if reason == reasons.SPOILED_INGREDIENT:
        if not spoiled:
            raise ActionError(400, "the reason Spoiled ingredient needs the spoiled ingredient")
        if not set(spoiled) <= on_ticket:
            raise ActionError(400, f"not on this ticket: {sorted(set(spoiled) - on_ticket)}")
    elif spoiled:
        raise ActionError(400, "spoiled ingredients go only with the reason Spoiled ingredient")
    spoiled = sorted(set(spoiled))
    _set(
        conn,
        rec,
        QUEUED,
        clock,
        status=CANCELLED,
        cancelled_by=KITCHEN,
        close_reason=reason,
        spoiled=spoiled,
    )
    _release(conn, rec, clock, cancelled_by=KITCHEN, reason=reason, spoiled=spoiled)
    rec.status, rec.cancelled_by, rec.close_reason, rec.spoiled = (
        CANCELLED,
        KITCHEN,
        reason,
        spoiled,
    )
    log.info("order_id=%s rejected: %s", order_id, reason)
    return rec


def complete(conn: psycopg.Connection[Any], order_id: uuid.UUID, clock: Clock) -> Record:
    """Cooking → Completed; reports Completed to the origin branch."""
    rec = _ticket(conn, order_id, COOKING)
    assert rec.origin_branch is not None
    _set(conn, rec, COOKING, clock, status=COMPLETED)
    _emit(conn, status_events(rec.origin_branch), "OrderCompleted", rec, clock, {})
    rec.status = COMPLETED
    log.info("order_id=%s completed", order_id)
    return rec


def list_tickets(conn: psycopg.Connection[Any]) -> list[Record]:
    """Queued and Cooking tickets, oldest order first. A Queued ticket carries a warning for
    each of its reserved ingredients that is flagged for stock check (a display-time join)."""
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM kitchen_orders WHERE status IN (%s, %s)"  # pyright: ignore[reportArgumentType]
        " ORDER BY order_created_at NULLS LAST, order_id",
        (QUEUED, COOKING),
    ).fetchall()
    flagged = {
        str(r[0])
        for r in conn.execute(
            "SELECT ingredient_id FROM flagged_ingredients WHERE needs_check"
        ).fetchall()
    }
    tickets = [_record(r) for r in rows]
    for t in tickets:
        if t.status == QUEUED:
            t.warnings = sorted({str(r.get("ingredient_id")) for r in t.reserved or []} & flagged)
    return tickets


def _ticket(conn: psycopg.Connection[Any], order_id: uuid.UUID, required: str) -> Record:
    rec = _lock(conn, order_id, create=False)
    if rec is None or rec.status == NONE:
        raise ActionError(404, f"no ticket for order {order_id}")
    if rec.status != required:
        raise ActionError(409, f"the ticket is {rec.status}, not {required}", rec.status)
    return rec


def _wrong_branch_alert(
    conn: psycopg.Connection[Any], message: Incoming, origin: str, dismissed: list[str]
) -> None:
    source = message.source
    if source is None:
        raise ValueError("a wrong-branch alert needs the message's Kafka position")
    write_alert(
        conn,
        WRONG_BRANCH_CANCEL,
        order_id=message.envelope.order_id,
        event_id=message.envelope.event_id,
        source_topic=source.topic,
        source_partition=source.partition,
        source_offset=source.offset,
        detail={"origin_branch": origin, "dismissed": dismissed},
    )


def _order_id(env: Envelope) -> uuid.UUID:
    if env.order_id is None:
        raise ValueError(f"{env.event_type} has no order_id")
    return env.order_id


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def ticket_view(rec: Record) -> dict[str, Any]:
    """A ticket as ``GET /tickets`` returns it."""
    return {
        "order_id": str(rec.order_id),
        "status": rec.status,
        "origin_branch": rec.origin_branch,
        "order_created_at": None
        if rec.order_created_at is None
        else rec.order_created_at.isoformat(),
        "items": rec.items or [],
        "reserved": rec.reserved or [],
        "warnings": rec.warnings,
    }
