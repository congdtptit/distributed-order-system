"""HTTP entry point of the Branch service (POS and Online, told apart by ``BRANCH_ID``), and
its background workers.

On start: the dish catalogue is loaded from the seed file; the replication heartbeat, the
consumer of ``status-events.<branch>`` and the sender of the send queue run in threads.

The APIs are in section 6 of docs/02-detailed-design.md. Invalid input is answered with 400,
not FastAPI's usual 422: BR9 names 400 for an order with invalid data.
"""

import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt

from common.api import get_clock, get_conn
from common.clock import Clock, SystemClock
from common.consumer import ConsumerSettings, MessageConsumer
from common.kafka import Receiver, Sender
from common.runtime import Workers, configure_logging, instance_name
from common.seed import load_menu
from common.service import identity
from common.topics import status_events
from order_service.heartbeat import Heartbeat
from order_service.monitor import MonitorLimits, monitor_view
from order_service.orders import (
    Line,
    OrderClosed,
    OrderNotFound,
    OrderRejected,
    cancel_order,
    create_order,
    get_order,
    list_dishes,
    list_orders,
    load_dishes,
)
from order_service.sender import UNKNOWN, ConnectionStatus, SendQueue
from order_service.statuses import branch_handlers

log = logging.getLogger(__name__)


def start_workers(
    workers: Workers, dsn: str, bootstrap: str | None, branch: str
) -> SendQueue | None:
    """The replication heartbeat always; the consumer and the send queue when Kafka is set."""

    def connect() -> psycopg.Connection[Any]:
        return psycopg.connect(dsn)

    workers.start("replication-heartbeat", Heartbeat(connect, branch).run)
    if not bootstrap:
        return None
    clock = SystemClock()
    name = instance_name()
    consumer = MessageConsumer(
        ConsumerSettings(
            name=f"branch-{branch}@{name}", handlers=branch_handlers(branch), deciding=False
        ),
        Receiver(bootstrap, f"branch-{branch}", [status_events(branch)], f"{name}-consumer"),
        Sender(bootstrap, f"{name}-dlq"),
        connect,
    )
    queue = SendQueue(connect, Sender(bootstrap, f"{name}-sender"), clock)
    workers.start("consumer", consumer.run)
    workers.start("send-queue", queue.run)
    return queue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn) as conn:
        load_dishes(conn, load_menu())
    workers = Workers()
    app.state.send_queue = start_workers(
        workers, dsn, os.environ.get("KAFKA_BOOTSTRAP"), get_branch()
    )
    try:
        yield
    finally:
        workers.stop()


app = FastAPI(title="Branch", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


def get_branch() -> str:
    return os.environ["BRANCH_ID"]


def get_connection_status(request: Request) -> ConnectionStatus:
    queue: SendQueue | None = getattr(request.app.state, "send_queue", None)
    return UNKNOWN if queue is None else queue.status


def get_limits() -> MonitorLimits:
    return MonitorLimits()


Conn = Annotated[psycopg.Connection[Any], Depends(get_conn)]
ClockDep = Annotated[Clock, Depends(get_clock)]
Branch = Annotated[str, Depends(get_branch)]
BAD_INPUT: dict[int | str, dict[str, Any]] = {400: {"description": "Invalid input"}}
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "No such order"}}


# ---------- models ----------


class NewLine(BaseModel):
    dish_id: str
    quantity: StrictInt


class NewOrder(BaseModel):
    items: list[NewLine]


class CancelRequest(BaseModel):
    reason_code: str
    """One of the customer cancel reasons (section 10): CHANGED_MIND, WAITED_TOO_LONG,
    WRONG_ORDER_ENTERED."""


class Item(BaseModel):
    dish_id: str
    name: str
    quantity: int


class Order(BaseModel):
    order_id: uuid.UUID
    branch_id: str
    status: str
    close_reason: str | None
    cancel_flag: str
    cancel_requested_at: datetime | None
    cancel_message: str | None
    items: list[Item]
    created_at: datetime
    send_state: str | None
    """The create-order entry: CHUA_GUI (not sent, the kitchen has not received it),
    DANG_GUI (sending, unknown whether the kitchen has it), DA_GUI (acknowledged by Kafka);
    null after a local cancel discarded it (BR5)."""
    cancel_send_state: str | None
    """The latest cancel entry, same values; null if no cancel request was queued."""


class Dish(BaseModel):
    dish_id: str
    name: str


class Connection(BaseModel):
    connected: bool | None
    """The most recent connectivity probe to Kafka; null before the first."""
    checked_at: datetime | None


class AwaitingOrder(BaseModel):
    order_id: uuid.UUID
    created_at: datetime
    waited_s: int
    cancel_flag: str


class ExpiringOrder(BaseModel):
    order_id: uuid.UUID
    created_at: datetime
    expires_at: datetime


class CancelWaiting(BaseModel):
    order_id: uuid.UUID
    cancel_flag: str
    cancel_requested_at: datetime | None
    waited_s: int | None


class MessageAlert(BaseModel):
    kind: str
    order_id: uuid.UUID | None
    event_id: uuid.UUID | None
    source_topic: str
    detail: dict[str, Any]
    created_at: datetime


class MessageAlerts(BaseModel):
    count: int
    latest: list[MessageAlert]


class Monitor(BaseModel):
    connection: Connection
    waiting_to_send: int
    """Entries in the send queue that Kafka has not acknowledged."""
    awaiting_inventory: list[AwaitingOrder]
    """Orders in Awaiting Inventory for longer than N minutes (scenario 53)."""
    about_to_expire: list[ExpiringOrder]
    """Orders still in the send queue less than 1 hour before the X-hour limit (scenario 54)."""
    cancel_requested: list[CancelWaiting]
    """Orders with the "Cancel requested" flag and the time waited so far."""
    message_alerts: MessageAlerts
    """Status messages this branch could not read or did not recognise (section 9)."""


# ---------- APIs ----------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", **identity()}


@app.get("/dishes")
def dishes(conn: Conn) -> list[Dish]:
    """The branch's own dish catalogue; answers while the branch is offline."""
    return [Dish(**d) for d in list_dishes(conn)]


@app.post("/orders", status_code=201, responses=BAD_INPUT)
def place_order(body: NewOrder, conn: Conn, clock: ClockDep, branch: Branch) -> Order:
    """Stores the Awaiting Inventory order and its create-order entry; does not wait for
    Inventory, whose result arrives later through ``status-events``."""
    lines = [Line(item.dish_id, item.quantity) for item in body.items]
    try:
        order = create_order(conn, branch, lines, clock)
    except OrderRejected as exc:
        raise HTTPException(400, {"message": str(exc)}) from exc
    conn.commit()  # before the response: a 201 means the order is stored
    return Order(**order)


@app.get("/orders", responses=BAD_INPUT)
def orders(conn: Conn, limit: Annotated[int, Query(ge=1, le=200)] = 200) -> list[Order]:
    """The newest orders first; ``limit`` (at most 200) lets the screen ask for one page."""
    return [Order(**o) for o in list_orders(conn, limit)]


@app.get("/orders/{order_id}", responses=NOT_FOUND)
def order(order_id: uuid.UUID, conn: Conn) -> Order:
    found = get_order(conn, order_id)
    if found is None:
        raise HTTPException(404, {"message": "no such order"})
    return Order(**found)


@app.post(
    "/orders/{order_id}/cancel",
    responses={
        **BAD_INPUT,
        **NOT_FOUND,
        202: {"description": "Sent to the Kitchen, or a cancel request is already waiting"},
        409: {"description": "The order is already in a terminal status"},
    },
)
def cancel(
    order_id: uuid.UUID,
    body: CancelRequest,
    response: Response,
    conn: Conn,
    clock: ClockDep,
    branch: Branch,
) -> Order:
    """200 with DA_HUY: cancelled here, the order was never attempted. 202 with the flag
    DANG_YEU_CAU: the Kitchen decides."""
    try:
        result = cancel_order(conn, branch, order_id, body.reason_code, clock)
    except ValueError as exc:
        raise HTTPException(400, {"message": str(exc)}) from exc
    except OrderNotFound as exc:
        raise HTTPException(404, {"message": "no such order"}) from exc
    except OrderClosed as exc:
        raise HTTPException(409, {"message": str(exc), "status": exc.status}) from exc
    conn.commit()
    response.status_code = 200 if result.local else 202
    return Order(**result.order)


@app.get("/monitor")
def monitor(
    conn: Conn,
    clock: ClockDep,
    connection: Annotated[ConnectionStatus, Depends(get_connection_status)],
    limits: Annotated[MonitorLimits, Depends(get_limits)],
) -> Monitor:
    return Monitor(**monitor_view(conn, connection, clock, limits))
