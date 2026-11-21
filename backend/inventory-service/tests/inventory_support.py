"""Helpers shared by the Inventory tests: build messages, deliver them through the same
deduplication as the consumer (``handle_once``), and read the Inventory DB."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg

from common.clock import Clock, FixedClock
from common.consumer import Incoming, handle_once
from common.envelope import Envelope, new_envelope
from common.seed import load_menu
from common.topics import branch_from_topic
from inventory_service.invariants import violations
from inventory_service.orders import Limits, make_order_created_handler
from inventory_service.stock import load_seed

NOW = datetime(2026, 11, 20, 9, 15, tzinfo=UTC)
D = Decimal


def seeded(dsn: str) -> str:
    """Load backend/seed/menu.json into a migrated Inventory DB."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        assert load_seed(conn, load_menu())
    return dsn


def order_created(
    *,
    order_id: uuid.UUID | None = None,
    created_at: datetime = NOW,
    items: list[tuple[str, int]] | None = None,
    payload: dict[str, Any] | None = None,
    branch_id: str = "POS01",
) -> Envelope:
    """An ``OrderCreated`` (section 2 of document 02). ``payload`` replaces the whole payload."""
    lines = items if items is not None else [("PHO_BO", 1)]
    body = (
        payload
        if payload is not None
        else {
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "channel": "POS",
            "items": [{"dish_id": d, "name": d.title(), "quantity": q} for d, q in lines],
        }
    )
    return new_envelope(
        "OrderCreated",
        order_id=order_id or uuid.uuid4(),
        branch_id=branch_id,
        clock=FixedClock(created_at),
        payload=body,
    )


def resend_with_new_event_id(env: Envelope) -> Envelope:
    """The same order in a new message (the second kind of duplicate in section 12)."""
    return Envelope(
        event_id=uuid.uuid4(),
        event_type=env.event_type,
        order_id=env.order_id,
        branch_id=env.branch_id,
        occurred_at=env.occurred_at,
        payload=env.payload,
    )


def deliver(
    dsn: str,
    env: Envelope,
    *,
    topic: str = "order-events.POS01",
    clock: Clock | None = None,
    limits: Limits | None = None,
    conn: psycopg.Connection[Any] | None = None,
) -> bool:
    """Process one message as the consumer would (steps 1 to 4). False if it was a duplicate."""
    handler = make_order_created_handler(clock or FixedClock(NOW), limits or Limits())
    message = Incoming(env, branch_from_topic(topic))
    if conn is not None:
        return handle_once(conn, handler, message)
    with psycopg.connect(dsn, autocommit=True) as own:
        return handle_once(own, handler, message)


@dataclass(frozen=True)
class Stock:
    available: Decimal
    reserved: Decimal
    consumed: Decimal
    wasted: Decimal
    needs_check: bool


@dataclass(frozen=True)
class OutboxRow:
    topic: str
    key: str
    event_type: str
    event_id: str
    causation_id: str | None
    branch_id: str | None
    payload: dict[str, Any]


def stock(dsn: str) -> dict[str, Stock]:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT ingredient_id, available, reserved, consumed, wasted, needs_check FROM stock"
        ).fetchall()
    return {str(r[0]): Stock(r[1], r[2], r[3], r[4], bool(r[5])) for r in rows}


def order_record(dsn: str, order_id: uuid.UUID | None) -> tuple[Any, ...] | None:
    """(status, reason, origin_branch, order_created_at) of the order's record."""
    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT status, reason, origin_branch, order_created_at FROM inventory_orders"
            " WHERE order_id = %s",
            (order_id,),
        ).fetchone()


def reservations(dsn: str, order_id: uuid.UUID | None) -> dict[str, Decimal]:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT ingredient_id, quantity FROM inventory_reservations"
            " WHERE order_id = %s AND outcome IS NULL",
            (order_id,),
        ).fetchall()
    return {str(r[0]): r[1] for r in rows}


def outbox(dsn: str) -> list[OutboxRow]:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT topic, msg_key, payload FROM outbox_events ORDER BY id"
        ).fetchall()
    return [
        OutboxRow(
            topic=str(r[0]),
            key=str(r[1]),
            event_type=r[2]["event_type"],
            event_id=r[2]["event_id"],
            causation_id=r[2]["causation_id"],
            branch_id=r[2]["branch_id"],
            payload=r[2]["payload"],
        )
        for r in rows
    ]


def processed(dsn: str) -> set[uuid.UUID]:
    with psycopg.connect(dsn) as conn:
        return {r[0] for r in conn.execute("SELECT event_id FROM processed_events").fetchall()}


def set_available(dsn: str, ingredient_id: str, available: Decimal) -> None:
    """Test setup: put an ingredient's available stock at a given value."""
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE stock SET available = %s WHERE ingredient_id = %s", (available, ingredient_id)
        )


def flag_for_stock_check(dsn: str, ingredient_id: str) -> None:
    """Test setup: the flag that step 3 sets when an ingredient is written off as waste."""
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE stock SET needs_check = TRUE WHERE ingredient_id = %s", (ingredient_id,)
        )


def assert_invariants(dsn: str) -> None:
    """Section 3 of document 02: run after every Inventory test."""
    with psycopg.connect(dsn) as conn:
        assert violations(conn) == {}
