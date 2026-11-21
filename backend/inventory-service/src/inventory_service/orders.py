"""Inventory receives ``OrderCreated``.

Table 3.3 of docs/01-business-spec.md, rows "(none) → Held", "(none) → Failed" and "duplicate
order arrives"; BR1, BR6, BR11, BR12; the base flow in section 4; the SQL of section 13.4. The
schema rules are in section 3 of docs/02-detailed-design.md.

The checks run in the order of the base flow: an order that already has a record gets the
stored result back (step 2); invalid order data and the time limit come next (step 3, invalid
data first because the time limit needs a readable creation time); then a dish with no recipe,
and finally the reservation itself (step 4).
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import psycopg

from common import reasons
from common.clock import Clock
from common.consumer import Handler, Incoming
from common.envelope import Envelope, new_envelope
from common.outbox import enqueue
from common.topics import KITCHEN_ORDERS, status_events

log = logging.getLogger(__name__)

HELD = "DANG_GIU"
FAILED = "THAT_BAI"
CHANNELS = frozenset({"POS", "ONLINE"})
MAX_QUANTITY = Decimal("999999999.999")
"""The largest value NUMERIC(12,3) holds; a larger demand can never be in stock."""


@dataclass(frozen=True)
class Limits:
    """BR11. Section 10 of the specification: X = 4 hours, tolerance 5 minutes (proposed)."""

    expiry: timedelta = timedelta(hours=4)
    future_tolerance: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class OrderLine:
    dish_id: str
    quantity: int


@dataclass(frozen=True)
class Order:
    created_at: datetime
    lines: tuple[OrderLine, ...]


@dataclass(frozen=True)
class Reserved:
    ingredient_id: str
    name: str
    unit: str
    quantity: Decimal


class _Short(Exception):
    def __init__(self, ingredient_id: str) -> None:
        super().__init__(ingredient_id)
        self.ingredient_id = ingredient_id


def parse_order(payload: dict[str, Any]) -> Order | None:
    """The ``OrderCreated`` payload of section 2 of document 02, or None if the order data is
    invalid: a missing required field, a wrong type, no items, or a quantity that is not a
    positive whole number of portions (base flow, step 4)."""
    created_raw = payload.get("created_at")
    if not isinstance(created_raw, str):
        return None
    try:
        created_at = datetime.fromisoformat(created_raw)
    except ValueError:
        return None
    if created_at.tzinfo is None or payload.get("channel") not in CHANNELS:
        return None
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return None
    lines: list[OrderLine] = []
    for raw in cast(list[object], items):
        if not isinstance(raw, dict):
            return None
        item = cast(dict[str, object], raw)
        dish_id, quantity, name = item.get("dish_id"), item.get("quantity"), item.get("name")
        if not isinstance(dish_id, str) or not dish_id:
            return None
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return None
        if name is not None and not isinstance(name, str):
            return None
        lines.append(OrderLine(dish_id, quantity))
    return Order(created_at, tuple(lines))


def make_order_created_handler(clock: Clock, limits: Limits) -> Handler:
    def handle(conn: psycopg.Connection[Any], message: Incoming) -> None:
        env = message.envelope
        origin = message.source_branch
        if origin is None:
            raise ValueError(f"{env.event_type} arrived on a topic that names no branch")
        if env.order_id is None:
            raise ValueError(f"{env.event_type} has no order_id")
        now = clock.now()

        order = parse_order(env.payload)
        failure = reasons.INVALID_ORDER_DATA if order is None else _time_failure(order, now, limits)
        inserted = conn.execute(
            """
            INSERT INTO inventory_orders
                   (order_id, origin_branch, status, reason, order_created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO NOTHING
            """,
            (
                env.order_id,
                origin,
                FAILED if failure else HELD,
                failure,
                None if order is None else order.created_at,
                now,
            ),
        ).rowcount
        if inserted == 0:
            _return_stored_result(conn, env, clock)  # BR12: never evaluated again
            return

        reserved: list[Reserved] = []
        if failure is None:
            assert order is not None
            failure, reserved = _reserve(conn, env, order)
            if failure is not None:
                conn.execute(
                    "UPDATE inventory_orders SET status = %s, reason = %s, updated_at = %s"
                    " WHERE order_id = %s",
                    (FAILED, failure, now, env.order_id),
                )

        if failure is not None:
            payload = {"origin_branch": origin, "reason_code": failure}
            for topic in (KITCHEN_ORDERS, status_events(origin)):
                enqueue(conn, topic, _reply("OrderFailed", env, origin, clock, payload))
            log.info("order_id=%s event_id=%s failed: %s", env.order_id, env.event_id, failure)
            return

        kitchen_payload: dict[str, Any] = {
            "origin_branch": origin,
            "created_at": env.payload["created_at"],
            "items": env.payload["items"],
            "reserved": [
                {
                    "ingredient_id": r.ingredient_id,
                    "name": r.name,
                    "unit": r.unit,
                    "quantity": float(r.quantity),
                }
                for r in reserved
            ],
        }
        enqueue(conn, KITCHEN_ORDERS, _reply("OrderReserved", env, origin, clock, kitchen_payload))
        enqueue(conn, status_events(origin), _reply("OrderReserved", env, origin, clock, {}))
        log.info("order_id=%s event_id=%s reserved", env.order_id, env.event_id)

    return handle


def _time_failure(order: Order, now: datetime, limits: Limits) -> str | None:
    """BR11: created more than X hours ago, or later than now plus the tolerance."""
    if order.created_at < now - limits.expiry:
        return reasons.ORDER_EXPIRED
    if order.created_at > now + limits.future_tolerance:
        return reasons.FUTURE_CREATION_TIME
    return None


def _reserve(
    conn: psycopg.Connection[Any], env: Envelope, order: Order
) -> tuple[str | None, list[Reserved]]:
    """Reserve every ingredient of the order or none (BR1). Returns (failure reason, lines)."""
    dish_ids = sorted({line.dish_id for line in order.lines})
    recipes: dict[str, list[tuple[str, Decimal]]] = defaultdict(list)
    for dish_id, ingredient_id, quantity in conn.execute(
        "SELECT dish_id, ingredient_id, quantity FROM recipes WHERE dish_id = ANY(%s)",
        (dish_ids,),
    ).fetchall():
        recipes[str(dish_id)].append((str(ingredient_id), Decimal(quantity)))
    if any(dish_id not in recipes for dish_id in dish_ids):
        return reasons.NO_RECIPE, []

    # The demand of the whole order per ingredient, so each ingredient has one UPDATE.
    demand: dict[str, Decimal] = defaultdict(Decimal)
    for line in order.lines:
        for ingredient_id, quantity in recipes[line.dish_id]:
            demand[ingredient_id] += quantity * line.quantity

    # Lock every stock row of the order in ascending ID (section 13.4: no deadlock between
    # orders) and decide from the locked rows, so the reason cannot change under us. A flagged
    # ingredient decides the reason even when another one is also short (BR6).
    locked: dict[str, tuple[Decimal, bool]] = {}
    for ingredient_id in sorted(demand):
        row = conn.execute(
            "SELECT available, needs_check FROM stock WHERE ingredient_id = %s FOR UPDATE",
            (ingredient_id,),
        ).fetchone()
        assert row is not None  # recipes.ingredient_id references stock
        locked[ingredient_id] = (Decimal(row[0]), bool(row[1]))
    if any(flagged for _available, flagged in locked.values()):
        return reasons.AWAITING_STOCK_CHECK, []
    if any(demand[i] > min(available, MAX_QUANTITY) for i, (available, _f) in locked.items()):
        return reasons.INSUFFICIENT_INGREDIENTS, []

    reserved: list[Reserved] = []
    try:
        with conn.transaction():  # SAVEPOINT reserve
            for ingredient_id in sorted(demand):
                q = demand[ingredient_id]
                # The statement of section 13.4, condition included. The rows are locked and
                # were just checked, so it always deducts; the condition stays as a safeguard.
                row = conn.execute(
                    """
                    UPDATE stock SET available = available - %s, reserved = reserved + %s
                     WHERE ingredient_id = %s AND available >= %s AND NOT needs_check
                    RETURNING name, unit
                    """,
                    (q, q, ingredient_id, q),
                ).fetchone()
                if row is None:
                    raise _Short(ingredient_id)
                conn.execute(
                    "INSERT INTO inventory_reservations (order_id, ingredient_id, quantity)"
                    " VALUES (%s, %s, %s)",
                    (env.order_id, ingredient_id, q),
                )
                reserved.append(Reserved(ingredient_id, str(row[0]), str(row[1]), q))
    except _Short:
        return reasons.INSUFFICIENT_INGREDIENTS, []
    return None, reserved


def _return_stored_result(conn: psycopg.Connection[Any], env: Envelope, clock: Clock) -> None:
    """A new ``event_id`` for an order that already has a record: emit the stored result to the
    origin branch only, not again to the Kitchen (section 3 of document 02, point 10)."""
    row = conn.execute(
        "SELECT status, reason, origin_branch FROM inventory_orders WHERE order_id = %s",
        (env.order_id,),
    ).fetchone()
    assert row is not None
    status, reason, origin = str(row[0]), row[1], str(row[2])
    if status == FAILED:
        reply = _reply(
            "OrderFailed", env, origin, clock, {"origin_branch": origin, "reason_code": reason}
        )
    else:
        reply = _reply("OrderReserved", env, origin, clock, {})
    enqueue(conn, status_events(origin), reply)
    log.info(
        "order_id=%s event_id=%s resent: returned the stored result %s",
        env.order_id,
        env.event_id,
        status,
    )


def _reply(
    event_type: str, cause: Envelope, origin: str, clock: Clock, payload: dict[str, Any]
) -> Envelope:
    return new_envelope(
        event_type,
        order_id=cause.order_id,
        branch_id=origin,
        clock=clock,
        payload=payload,
        causation_id=cause.event_id,
    )
