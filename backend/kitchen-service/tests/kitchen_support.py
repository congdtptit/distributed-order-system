"""Helpers shared by the Kitchen tests: Inventory's messages as the Kitchen receives them,
delivery through the consumer's deduplication (``handle_once``), and readers of the Kitchen DB."""

import itertools
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import inventory_support as inv
import psycopg

from common.clock import Clock, FixedClock
from common.consumer import Incoming, Source, handle_once
from common.envelope import Envelope, decode, new_envelope
from common.topics import branch_from_topic
from kitchen_service.app import kitchen_handlers

NOW = datetime(2026, 11, 20, 9, 15, tzinfo=UTC)
_offsets = itertools.count()

PHO_BO_RESERVED = [
    {"ingredient_id": "BANH_PHO", "name": "Bánh phở", "unit": "kg", "quantity": 0.2},
    {"ingredient_id": "RAU_SONG", "name": "Rau sống", "unit": "kg", "quantity": 0.05},
    {"ingredient_id": "THIT_BO", "name": "Thịt bò", "unit": "kg", "quantity": 0.15},
]
BUN_CHA_RESERVED = [
    {"ingredient_id": "BUN", "name": "Bún", "unit": "kg", "quantity": 0.2},
    {"ingredient_id": "RAU_SONG", "name": "Rau sống", "unit": "kg", "quantity": 0.05},
    {"ingredient_id": "THIT_LON", "name": "Thịt lợn", "unit": "kg", "quantity": 0.15},
]


def order_reserved(
    order_id: uuid.UUID | None = None,
    *,
    origin: str = "POS01",
    reserved: list[dict[str, Any]] | None = None,
    dish: str = "PHO_BO",
) -> Envelope:
    """Inventory's ``OrderReserved`` on ``kitchen-orders`` (section 2 of document 02)."""
    return new_envelope(
        "OrderReserved",
        order_id=order_id or uuid.uuid4(),
        branch_id=origin,
        clock=FixedClock(NOW),
        payload={
            "origin_branch": origin,
            "created_at": "2026-11-20T09:15:00Z",
            "items": [{"dish_id": dish, "name": dish.title(), "quantity": 1}],
            "reserved": reserved if reserved is not None else PHO_BO_RESERVED,
        },
    )


def order_failed(
    order_id: uuid.UUID | None = None,
    *,
    origin: str = "POS01",
    reason: str = "INSUFFICIENT_INGREDIENTS",
) -> Envelope:
    return new_envelope(
        "OrderFailed",
        order_id=order_id or uuid.uuid4(),
        branch_id=origin,
        clock=FixedClock(NOW),
        payload={"origin_branch": origin, "reason_code": reason},
    )


def cancel_requested(
    order_id: uuid.UUID | None, *, branch: str = "POS01", reason: str = "CHANGED_MIND"
) -> Envelope:
    """A branch's cancel request; ``deliver`` sends it on ``cancel-events.<branch>``."""
    return new_envelope(
        "CancelRequested",
        order_id=order_id,
        branch_id=branch,
        clock=FixedClock(NOW),
        payload={"reason_code": reason},
    )


def check_changed(ingredient_id: str, needs_check: bool, seq: int, epoch: int = 1) -> Envelope:
    return new_envelope(
        "IngredientCheckChanged",
        order_id=None,
        branch_id=None,
        clock=FixedClock(NOW),
        payload={
            "ingredient_id": ingredient_id,
            "needs_check": needs_check,
            "epoch": epoch,
            "seq": seq,
        },
    )


def deliver(
    dsn: str,
    env: Envelope,
    *,
    topic: str | None = None,
    clock: Clock | None = None,
    conn: psycopg.Connection[Any] | None = None,
) -> bool:
    """Process one message as the consumer would (steps 1 to 4); False for a duplicate."""
    if topic is None:
        topic = {
            "IngredientCheckChanged": "menu-events",
            "CancelRequested": f"cancel-events.{env.branch_id}",
        }.get(env.event_type, "kitchen-orders")
    handler = kitchen_handlers(clock or FixedClock(NOW))[env.event_type]
    message = Incoming(env, branch_from_topic(topic), Source(topic, 0, next(_offsets)))
    if conn is not None:
        return handle_once(conn, handler, message)
    with psycopg.connect(dsn, autocommit=True) as own:
        return handle_once(own, handler, message)


@dataclass(frozen=True)
class Sent:
    topic: str
    key: str
    event_type: str
    causation_id: str | None
    payload: dict[str, Any]


def outbox(dsn: str) -> list[Sent]:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT topic, msg_key, payload FROM outbox_events ORDER BY id"
        ).fetchall()
    return [
        Sent(str(r[0]), str(r[1]), r[2]["event_type"], r[2]["causation_id"], r[2]["payload"])
        for r in rows
    ]


def sent_envelopes(dsn: str, event_type: str, topic: str | None = None) -> list[Envelope]:
    """The messages of one type (on one topic, if given) in a service's outbox, Inventory's or
    the Kitchen's, as the receiver would decode them: to hand real messages between services."""
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT payload FROM outbox_events WHERE payload->>'event_type' = %s"
            " AND (%s::text IS NULL OR topic = %s) ORDER BY id",
            (event_type, topic, topic),
        ).fetchall()
    return [decode(json.dumps(r[0]).encode()) for r in rows]


def through_inventory(idb: str, order: Envelope) -> Envelope:
    """Inventory's real handler takes the order; returns what it sent to ``kitchen-orders``
    (OrderReserved or OrderFailed)."""
    inv.deliver(idb, order)
    for event_type in ("OrderReserved", "OrderFailed"):
        found = [
            e
            for e in sent_envelopes(idb, event_type, "kitchen-orders")
            if e.causation_id == order.event_id
        ]
        if found:
            [to_kitchen] = found
            return to_kitchen
    raise AssertionError("Inventory sent nothing to kitchen-orders")


def record(dsn: str, order_id: uuid.UUID | None) -> dict[str, Any] | None:
    with psycopg.connect(dsn) as conn:
        cur = conn.execute(
            "SELECT status, origin_branch, cancelled_by, close_reason, spoiled, reserved,"
            " cancel_branches, cancel_reasons"
            " FROM kitchen_orders WHERE order_id = %s",
            (order_id,),
        )
        row = cur.fetchone()
        names = [d.name for d in cur.description or []]
    return None if row is None else dict(zip(names, row, strict=True))


def records_count(dsn: str) -> int:
    with psycopg.connect(dsn) as conn:
        row = conn.execute("SELECT count(*) FROM kitchen_orders").fetchone()
    assert row is not None
    return int(row[0])


def alerts(dsn: str) -> list[tuple[Any, ...]]:
    """(kind, order_id, detail) of every alert."""
    with psycopg.connect(dsn) as conn:
        return conn.execute("SELECT kind, order_id, detail FROM alerts ORDER BY id").fetchall()
