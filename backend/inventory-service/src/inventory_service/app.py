"""HTTP entry point of the Inventory service, and its background workers.

On start: load the seed if ``stock`` is empty (section 1 of docs/02-detailed-design.md), then
run the consumer of ``order-events.*`` and ``stock-commands`` and the outbox relay in threads.
Two instances share the consumer group ``inventory``, so Kafka splits the partitions between
them.

The APIs are in section 6 of docs/02-detailed-design.md.
"""

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.alerts import list_alerts
from common.api import get_clock, get_conn
from common.clock import Clock, SystemClock
from common.consumer import ConsumerSettings, MessageConsumer
from common.kafka import Receiver, Sender
from common.monitor import ConsumerMonitor
from common.outbox import OutboxRelay
from common.runtime import Workers, configure_logging, instance_name
from common.seed import load_menu
from common.service import identity
from common.topics import ORDER_EVENTS_PATTERN, STOCK_COMMANDS
from inventory_service.checks import ClearResult, clear_check
from inventory_service.commands import make_consumed_handler, make_release_handler
from inventory_service.dishes import (
    HEARTBEAT_EVERY_S,
    HeartbeatSender,
    bump_epoch,
    snapshot,
)
from inventory_service.orders import Limits, make_order_created_handler
from inventory_service.stock import load_seed, receive_stock

log = logging.getLogger(__name__)
CONSUMER_GROUP = "inventory"


def limits_from_env() -> Limits:
    return Limits(
        expiry=timedelta(hours=float(os.environ.get("ORDER_EXPIRY_HOURS", "4"))),
        future_tolerance=timedelta(minutes=float(os.environ.get("FUTURE_TOLERANCE_MINUTES", "5"))),
    )


def start_workers(dsn: str, bootstrap: str) -> Workers:
    clock = SystemClock()
    name = instance_name()

    def connect() -> psycopg.Connection[Any]:
        return psycopg.connect(dsn)

    consumer = MessageConsumer(
        ConsumerSettings(
            name=f"inventory@{name}",
            handlers={
                "OrderCreated": make_order_created_handler(clock, limits_from_env()),
                "ReleaseRequested": make_release_handler(clock),
                "StockConsumed": make_consumed_handler(clock),
            },
            deciding=True,
        ),
        Receiver(
            bootstrap, CONSUMER_GROUP, [ORDER_EVENTS_PATTERN, STOCK_COMMANDS], f"{name}-consumer"
        ),
        Sender(bootstrap, f"{name}-dlq"),
        connect,
    )
    relay = OutboxRelay(connect, Sender(bootstrap, f"{name}-relay"), clock)
    workers = Workers()
    workers.start("consumer", consumer.run)
    workers.start("outbox-relay", relay.run)
    every_s = float(os.environ.get("INVENTORY_HEARTBEAT_S", str(HEARTBEAT_EVERY_S)))
    workers.start("heartbeat", HeartbeatSender(connect, clock, every_s).run)
    return workers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn) as conn:
        conn.autocommit = True
        if load_seed(conn, load_menu()):
            log.info("seed loaded: ingredients, stock and recipes")
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    workers = start_workers(dsn, bootstrap) if bootstrap else None
    try:
        yield
    finally:
        if workers is not None:
            workers.stop()


app = FastAPI(title="Inventory", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", **identity()}


# ---------- the APIs of section 6 of docs/02-detailed-design.md ----------


Conn = Annotated[psycopg.Connection[Any], Depends(get_conn)]
ClockDep = Annotated[Clock, Depends(get_clock)]
Quantity = Annotated[Decimal, Field(max_digits=12, decimal_places=3)]


class StockItem(BaseModel):
    """The four quantities of section 3.3 of the specification and the stock-check flag."""

    ingredient_id: str
    name: str
    unit: str
    available: Decimal
    reserved: Decimal
    consumed: Decimal
    wasted: Decimal
    needs_check: bool


class Receipt(BaseModel):
    ingredient_id: str
    quantity: Annotated[Quantity, Field(gt=0)]


class ClearCheck(BaseModel):
    counted_on_hand: Annotated[Quantity, Field(ge=0)] | None = None
    """The counted on-hand stock (available plus reserved); omitted: available is unchanged."""


_STOCK_COLUMNS = "ingredient_id, name, unit, available, reserved, consumed, wasted, needs_check"


def _stock_item(conn: psycopg.Connection[Any], ingredient_id: str) -> StockItem:
    row = conn.execute(
        f"SELECT {_STOCK_COLUMNS} FROM stock WHERE ingredient_id = %s",  # pyright: ignore[reportArgumentType]
        (ingredient_id,),
    ).fetchone()
    assert row is not None
    return StockItem(**dict(zip(_STOCK_COLUMNS.split(", "), row, strict=True)))


@app.get("/stock")
def list_stock(conn: Conn) -> list[StockItem]:
    """Testing, the demo, and Flow D's list of ingredients awaiting a stock check."""
    rows = conn.execute(
        f"SELECT {_STOCK_COLUMNS} FROM stock ORDER BY ingredient_id"  # pyright: ignore[reportArgumentType]
    ).fetchall()
    return [StockItem(**dict(zip(_STOCK_COLUMNS.split(", "), r, strict=True))) for r in rows]


@app.post("/stock/receipts", responses={404: {"description": "No such ingredient"}})
def stock_receipt(body: Receipt, conn: Conn, clock: ClockDep) -> StockItem:
    """Stock receipt: adds to available stock and recomputes the ingredient's dishes."""
    if not receive_stock(conn, body.ingredient_id, body.quantity, clock):
        raise HTTPException(404, f"no ingredient {body.ingredient_id}")
    item = _stock_item(conn, body.ingredient_id)
    conn.commit()  # before the response: a 200 means the change is stored
    return item


@app.post(
    "/ingredients/{ingredient_id}/clear-check",
    responses={
        404: {"description": "No such ingredient"},
        409: {"description": "counted_on_hand is less than the reserved quantity"},
    },
)
def clear_stock_check(
    ingredient_id: str, conn: Conn, clock: ClockDep, body: ClearCheck | None = None
) -> StockItem:
    """Clear the stock-check flag once the check is done (Flow A, scenario 48)."""
    counted = None if body is None else body.counted_on_hand
    outcome = clear_check(conn, ingredient_id, counted, clock)
    if outcome.result is ClearResult.NOT_FOUND:
        raise HTTPException(404, f"no ingredient {ingredient_id}")
    if outcome.result is ClearResult.BELOW_RESERVED:
        raise HTTPException(
            409,
            {
                "message": "counted_on_hand is less than the reserved quantity; reject the"
                " tickets still holding this ingredient first (Flow A)",
                "reserved": str(outcome.reserved),
            },
        )
    item = _stock_item(conn, ingredient_id)
    conn.commit()  # before the response: a 200 means the change is stored
    return item


class DishVersion(BaseModel):
    dish_id: str
    status: Literal["CON", "HET", "AN"]
    epoch: int
    seq: int


class MenuSnapshot(BaseModel):
    epoch: int
    """The current epoch: a branch moves every dish still at an older epoch to Hidden."""
    dishes: list[DishVersion]


@app.get("/menu/snapshot")
def menu_snapshot(conn: Conn) -> MenuSnapshot:
    """Flow C: the status and version of every dish, Hidden ones included. The one API another
    service calls (a branch, on start, on reconnecting and on a new epoch)."""
    snap = snapshot(conn)
    return MenuSnapshot(
        epoch=snap.epoch,
        dishes=[DishVersion(**vars(d)) for d in snap.dishes],
    )


class Bumped(BaseModel):
    epoch: int


@app.post("/admin/epoch/bump")
def epoch_bump(conn: Conn, clock: ClockDep) -> Bumped:
    """After Inventory is restored from a backup (section 3 of document 02, scenario 20)."""
    epoch = bump_epoch(conn, clock)
    conn.commit()
    return Bumped(epoch=epoch)


class Alert(BaseModel):
    """A Flow D item a person needs to look at (the ``alerts`` table, section 3 of
    docs/02-detailed-design.md)."""

    id: int
    kind: str
    order_id: uuid.UUID | None
    event_id: uuid.UUID | None
    source_topic: str
    source_partition: int
    source_offset: int
    detail: dict[str, Any]
    created_at: datetime


@app.get("/alerts")
def alerts(
    conn: Conn, kind: Literal["CAN_KIEM_TRA", "LENH_KHONG_KHOP"] | None = None
) -> list[Alert]:
    """Orders that need review and unmatched commands,
    newest first (at most 100); ``kind`` filters."""
    return [Alert(**a) for a in list_alerts(conn, kind)]


class TopicState(BaseModel):
    topic: str
    unread: int
    oldest_unread_at: datetime | None
    oldest_unread_age_s: int | None
    slow: bool
    """The oldest unread message is older than ``slow_after_s`` (section 10: 5 minutes)."""


class Monitor(BaseModel):
    consumer_group: str
    slow_after_s: int
    kafka_reachable: bool
    topics: list[TopicState]


_monitor: ConsumerMonitor | None = None


def get_monitor() -> ConsumerMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ConsumerMonitor(
            os.environ.get("KAFKA_BOOTSTRAP"),
            CONSUMER_GROUP,
            [ORDER_EVENTS_PATTERN, STOCK_COMMANDS],
            SystemClock(),
        )
    return _monitor


@app.get("/monitor")
def monitor(consumer: Annotated[ConsumerMonitor, Depends(get_monitor)]) -> Monitor:
    """Flow D: unread messages per topic and the slow-consumer alert."""
    return Monitor(**consumer.view())
