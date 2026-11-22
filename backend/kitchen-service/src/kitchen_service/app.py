"""HTTP entry point of the Kitchen service, and its background workers.

On start: the consumer of ``kitchen-orders``, ``cancel-events.*`` and ``menu-events`` and the
outbox relay run in threads. Two instances share the consumer group ``kitchen``.

The APIs are in section 6 of docs/02-detailed-design.md.
"""

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from common.alerts import list_alerts
from common.api import get_clock, get_conn
from common.clock import Clock, SystemClock
from common.consumer import ConsumerSettings, Handler, MessageConsumer
from common.kafka import Receiver, Sender
from common.outbox import OutboxRelay
from common.runtime import Workers, configure_logging, instance_name
from common.service import identity
from common.topics import CANCEL_EVENTS_PATTERN, KITCHEN_ORDERS, MENU_EVENTS
from kitchen_service.tickets import (
    ActionError,
    Record,
    complete,
    list_tickets,
    make_cancel_requested_handler,
    make_check_changed_handler,
    make_order_failed_handler,
    make_order_reserved_handler,
    reject,
    start_cooking,
    ticket_view,
)

log = logging.getLogger(__name__)
CONSUMER_GROUP = "kitchen"


def kitchen_handlers(clock: Clock) -> dict[str, Handler]:
    return {
        "OrderReserved": make_order_reserved_handler(clock),
        "OrderFailed": make_order_failed_handler(clock),
        "CancelRequested": make_cancel_requested_handler(clock),
        "IngredientCheckChanged": make_check_changed_handler(),
    }


def start_workers(dsn: str, bootstrap: str) -> Workers:
    clock = SystemClock()
    name = instance_name()

    def connect() -> psycopg.Connection[Any]:
        return psycopg.connect(dsn)

    consumer = MessageConsumer(
        ConsumerSettings(name=f"kitchen@{name}", handlers=kitchen_handlers(clock), deciding=True),
        Receiver(
            bootstrap,
            CONSUMER_GROUP,
            [KITCHEN_ORDERS, CANCEL_EVENTS_PATTERN, MENU_EVENTS],
            f"{name}-consumer",
        ),
        Sender(bootstrap, f"{name}-dlq"),
        connect,
    )
    relay = OutboxRelay(connect, Sender(bootstrap, f"{name}-relay"), clock)
    workers = Workers()
    workers.start("consumer", consumer.run)
    workers.start("outbox-relay", relay.run)
    return workers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    workers = start_workers(os.environ["DATABASE_URL"], bootstrap) if bootstrap else None
    try:
        yield
    finally:
        if workers is not None:
            workers.stop()


app = FastAPI(title="Kitchen", lifespan=lifespan)

Conn = Annotated[psycopg.Connection[Any], Depends(get_conn)]
ClockDep = Annotated[Clock, Depends(get_clock)]
ACTION_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "No ticket for this order"},
    409: {"description": "The ticket is no longer in the required status (a lost race)"},
}


class ReservedLine(BaseModel):
    ingredient_id: str
    name: str | None = None
    unit: str | None = None
    quantity: float | None = None


class Ticket(BaseModel):
    order_id: str
    status: str
    origin_branch: str | None
    order_created_at: str | None
    items: list[dict[str, Any]]
    reserved: list[ReservedLine]
    warnings: list[str]
    """Reserved ingredients flagged for stock check (Queued tickets only, Flow A step 6)."""


class Rejection(BaseModel):
    reason_code: str
    spoiled_ingredients: list[str] = []


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", **identity()}


@app.get("/tickets")
def tickets(conn: Conn) -> list[Ticket]:
    return [Ticket(**ticket_view(t)) for t in list_tickets(conn)]


def _act(conn: psycopg.Connection[Any], action: Any) -> Ticket:
    try:
        rec: Record = action()
    except ActionError as exc:
        detail: dict[str, Any] = {"message": str(exc)}
        if exc.current is not None:
            detail["status"] = exc.current
        raise HTTPException(exc.status_code, detail) from exc
    conn.commit()  # before the response: a 200 means the change is stored
    return Ticket(**ticket_view(rec))


@app.post("/tickets/{order_id}/start", responses=ACTION_ERRORS)
def start(order_id: uuid.UUID, conn: Conn, clock: ClockDep) -> Ticket:
    """Queued → Cooking; emits StockConsumed."""
    return _act(conn, lambda: start_cooking(conn, order_id, clock))


@app.post(
    "/tickets/{order_id}/reject",
    responses={**ACTION_ERRORS, 400: {"description": "Bad reason or spoiled ingredients"}},
)
def reject_ticket(order_id: uuid.UUID, body: Rejection, conn: Conn, clock: ClockDep) -> Ticket:
    """Queued → Cancelled (Kitchen rejection); emits OrderCancelled and ReleaseRequested."""
    return _act(
        conn, lambda: reject(conn, order_id, body.reason_code, body.spoiled_ingredients, clock)
    )


@app.post("/tickets/{order_id}/complete", responses=ACTION_ERRORS)
def complete_ticket(order_id: uuid.UUID, conn: Conn, clock: ClockDep) -> Ticket:
    """Cooking → Completed; emits OrderCompleted."""
    return _act(conn, lambda: complete(conn, order_id, clock))


class Alert(BaseModel):
    """A Flow D item a person needs to look at (the ``alerts`` table, section 4 of
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
    conn: Conn, kind: Literal["CAN_KIEM_TRA", "HUY_SAI_CHI_NHANH"] | None = None
) -> list[Alert]:
    """Orders that need review and wrong-branch cancel requests,
    newest first (at most 100); ``kind`` filters."""
    return [Alert(**a) for a in list_alerts(conn, kind)]
