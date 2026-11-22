"""The branch's orders: placing an order, the cancel operation, and reading orders back.

Table 3.1 of docs/01-business-spec.md, BR5 and BR9; the "Branch side" of Flow B in section 6;
the schema and write (2) of section 5 of docs/02-detailed-design.md. Write (1) is the sender's
(``order_service.sender``), writes (3) to (5) apply status messages
(``order_service.statuses``).

The branch decides a status by itself in one case only: a cancel request for an order whose
create-order entry was never attempted closes the order as Cancelled and discards the entry.
Every other cancel goes to the Kitchen as a ``HUY`` entry in the send queue.
"""

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import psycopg
from psycopg.types.json import Jsonb

from common import reasons
from common.clock import Clock
from common.envelope import new_envelope
from common.seed import Menu
from common.topics import cancel_events, order_events

log = logging.getLogger(__name__)

AWAITING: Final = "CHO_KHO"
RESERVED: Final = "DA_GIU"
COMPLETED: Final = "HOAN_TAT"
CANCELLED: Final = "DA_HUY"
FAILED: Final = "THAT_BAI"
RANK: Final = {AWAITING: 0, RESERVED: 1, COMPLETED: 2, CANCELLED: 2, FAILED: 2}
"""Section 3.1 of the specification. Rank 2 is terminal."""
TERMINAL_RANK: Final = 2

FLAG_OFF: Final = "KHONG"
FLAG_REQUESTED: Final = "DANG_YEU_CAU"
"""Cancel requested, no reply from the Kitchen yet."""
FLAG_WILL_NOT_COOK: Final = "BEP_KHONG_NAU"
"""The Kitchen holds a Cancel-pending record: "kitchen will not cook"."""

CREATE_ENTRY: Final = "TAO_DON"
CANCEL_ENTRY: Final = "HUY"

NOT_SENT: Final = "CHUA_GUI"
"""Send state of an entry without the "send attempted" flag: certainly not in Kafka (BR5)."""
SENDING: Final = "DANG_GUI"
"""Attempted, not yet acknowledged: unknown whether Kafka has it."""
SENT: Final = "DA_GUI"
"""Acknowledged by Kafka. This does not mean Inventory or the Kitchen received it (BR9)."""


class OrderRejected(Exception):
    """Invalid order data (BR9): the order is refused with HTTP 400 and enters no queue."""


class OrderNotFound(Exception):
    pass


class OrderClosed(Exception):
    """A cancel for an order already in a terminal status (HTTP 409)."""

    def __init__(self, status: str) -> None:
        super().__init__(f"the order is already {status}")
        self.status = status


@dataclass(frozen=True)
class Line:
    dish_id: str
    quantity: int


@dataclass(frozen=True)
class CancelResult:
    local: bool
    """True: closed here as Cancelled (200). False: the request goes to the Kitchen, or one is
    already waiting (202)."""
    order: dict[str, Any]


# ---------- the dish catalogue ----------


def load_dishes(conn: psycopg.Connection[Any], menu: Menu) -> None:
    """Insert or update every dish of the seed file (section 1 of document 02), on every
    start. A dish dropped from the file stays: old orders keep their names anyway."""
    with conn.transaction():
        for dish in menu.dishes:
            conn.execute(
                "INSERT INTO dishes (dish_id, name) VALUES (%s, %s)"
                " ON CONFLICT (dish_id) DO UPDATE SET name = EXCLUDED.name",
                (dish.dish_id, dish.name),
            )


def list_dishes(conn: psycopg.Connection[Any]) -> list[dict[str, str]]:
    rows = conn.execute("SELECT dish_id, name FROM dishes ORDER BY dish_id").fetchall()
    return [{"dish_id": str(r[0]), "name": str(r[1])} for r in rows]


# ---------- placing an order ----------


def channel_of(branch: str) -> str:
    """``channel`` of ``OrderCreated``: the Online branch is ONLINE, every POS site is POS."""
    return "ONLINE" if branch == "ONLINE" else "POS"


def create_order(
    conn: psycopg.Connection[Any], branch: str, lines: Sequence[Line], clock: Clock
) -> dict[str, Any]:
    """Base flow step 1: validate, generate the order ID, store the Awaiting Inventory order
    and its create-order entry in one transaction (the caller commits). Works offline: nothing
    here talks to Kafka.

    Raises ``OrderRejected`` for invalid data: no lines, a quantity that is not a positive
    whole number, or a dish that is not in ``dishes``.
    """
    if not lines:
        raise OrderRejected("the order has no items")
    for line in lines:
        if line.quantity <= 0:
            raise OrderRejected(f"quantity of {line.dish_id} must be positive")
    names = dict(
        conn.execute(
            "SELECT dish_id, name FROM dishes WHERE dish_id = ANY(%s)",
            ([line.dish_id for line in lines],),
        ).fetchall()
    )
    unknown = sorted({line.dish_id for line in lines} - set(names))
    if unknown:
        raise OrderRejected(f"unknown dish: {', '.join(unknown)}")

    order_id = uuid.uuid4()
    created_at = clock.now()
    items = [
        {"dish_id": line.dish_id, "name": names[line.dish_id], "quantity": line.quantity}
        for line in lines
    ]
    conn.execute(
        "INSERT INTO orders (order_id, branch_id, status, status_rank, items, created_at)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (order_id, branch, AWAITING, RANK[AWAITING], Jsonb(items), created_at),
    )
    envelope = new_envelope(
        "OrderCreated",
        order_id=order_id,
        branch_id=branch,
        clock=clock,
        payload={
            "created_at": created_at.isoformat(),
            "channel": channel_of(branch),
            "items": items,
        },
    )
    _enqueue(conn, CREATE_ENTRY, order_events(branch), envelope.to_dict())
    log.info("order_id=%s created at %s, %d line(s)", order_id, branch, len(items))
    order = get_order(conn, order_id)
    assert order is not None
    return order


def _enqueue(
    conn: psycopg.Connection[Any], kind: str, topic: str, envelope: dict[str, Any]
) -> None:
    conn.execute(
        "INSERT INTO outbox_events (event_id, order_id, kind, topic, payload)"
        " VALUES (%s, %s, %s, %s, %s)",
        (envelope["event_id"], envelope["order_id"], kind, topic, Jsonb(envelope)),
    )


# ---------- the cancel operation: write (2) ----------


def cancel_order(
    conn: psycopg.Connection[Any],
    branch: str,
    order_id: uuid.UUID,
    reason_code: str,
    clock: Clock,
) -> CancelResult:
    """Write (2) of section 5 of document 02, in the caller's transaction (the caller commits).

    The ``orders`` row is locked first, so two presses in quick succession run one after the
    other, and a terminal status message arriving meanwhile (write (3)) waits for this one.
    Deleting the create-order entry ``WHERE attempted = FALSE`` locks the same row the sender's
    write (1) does, so exactly one of the two wins (scenario 37).
    """
    if reason_code not in reasons.CUSTOMER_CANCEL:
        raise ValueError(f"reason_code must be one of {sorted(reasons.CUSTOMER_CANCEL)}")
    row = conn.execute(
        "SELECT status, status_rank, cancel_flag FROM orders WHERE order_id = %s FOR UPDATE",
        (order_id,),
    ).fetchone()
    if row is None:
        raise OrderNotFound(str(order_id))
    status, rank, flag = str(row[0]), int(row[1]), str(row[2])
    if rank == TERMINAL_RANK:
        raise OrderClosed(status)
    if flag != FLAG_OFF:
        return CancelResult(local=False, order=_view(conn, order_id))  # no second HUY entry

    discarded = conn.execute(
        "DELETE FROM outbox_events"
        " WHERE order_id = %s AND kind = %s AND attempted = FALSE RETURNING id",
        (order_id, CREATE_ENTRY),
    ).fetchall()
    if discarded:
        # Never attempted: certainly not in Kafka, so the branch closes the order (BR9).
        conn.execute(
            "UPDATE orders SET status = %s, status_rank = %s, close_reason = %s"
            " WHERE order_id = %s",
            (CANCELLED, RANK[CANCELLED], reason_code, order_id),
        )
        log.info("order_id=%s cancelled locally: never attempted (%s)", order_id, reason_code)
        return CancelResult(local=True, order=_view(conn, order_id))

    envelope = new_envelope(
        "CancelRequested",
        order_id=order_id,
        branch_id=branch,
        clock=clock,
        payload={"reason_code": reason_code},
    )
    _enqueue(conn, CANCEL_ENTRY, cancel_events(branch), envelope.to_dict())
    conn.execute(
        "UPDATE orders SET cancel_flag = %s, cancel_requested_at = %s, cancel_message = NULL"
        " WHERE order_id = %s",
        (FLAG_REQUESTED, clock.now(), order_id),
    )
    log.info("order_id=%s cancel request queued for the Kitchen (%s)", order_id, reason_code)
    return CancelResult(local=False, order=_view(conn, order_id))


# ---------- reading ----------

_ORDER_COLUMNS: Final = """
    o.order_id, o.branch_id, o.status, o.close_reason, o.cancel_flag, o.cancel_requested_at,
    o.cancel_message, o.items, o.created_at,
    (SELECT CASE WHEN e.sent_at IS NOT NULL THEN 'DA_GUI'
                 WHEN e.attempted THEN 'DANG_GUI' ELSE 'CHUA_GUI' END
       FROM outbox_events e WHERE e.order_id = o.order_id AND e.kind = 'TAO_DON'
      ORDER BY e.id LIMIT 1) AS send_state,
    (SELECT CASE WHEN e.sent_at IS NOT NULL THEN 'DA_GUI'
                 WHEN e.attempted THEN 'DANG_GUI' ELSE 'CHUA_GUI' END
       FROM outbox_events e WHERE e.order_id = o.order_id AND e.kind = 'HUY'
      ORDER BY e.id DESC LIMIT 1) AS cancel_send_state
"""


def _rows_to_views(cur: psycopg.Cursor[Any]) -> list[dict[str, Any]]:
    names = [d.name for d in cur.description or []]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def get_order(conn: psycopg.Connection[Any], order_id: uuid.UUID) -> dict[str, Any] | None:
    """One order with its cancel flag and message, and the send state of its create-order
    entry (``send_state``: ``CHUA_GUI``, ``DANG_GUI``, ``DA_GUI``; null once discarded by a
    local cancel) and of its latest cancel entry (``cancel_send_state``, null if none)."""
    cur = conn.execute(
        f"SELECT {_ORDER_COLUMNS} FROM orders o WHERE o.order_id = %s",
        (order_id,),
    )
    views = _rows_to_views(cur)
    return views[0] if views else None


def _view(conn: psycopg.Connection[Any], order_id: uuid.UUID) -> dict[str, Any]:
    order = get_order(conn, order_id)
    assert order is not None
    return order


def list_orders(conn: psycopg.Connection[Any], limit: int = 200) -> list[dict[str, Any]]:
    """The most recent orders first."""
    cur = conn.execute(
        f"SELECT {_ORDER_COLUMNS} FROM orders o ORDER BY o.created_at DESC, o.order_id LIMIT %s",
        (limit,),
    )
    return _rows_to_views(cur)
