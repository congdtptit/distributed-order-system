"""HTTP entry point of the Inventory service, and its background workers.

On start: load the seed if ``stock`` is empty (section 1 of docs/02-detailed-design.md), then
run the consumer of ``order-events.*`` and the outbox relay in threads. Two instances share the
consumer group ``inventory``, so Kafka splits the partitions between them.

The APIs are in section 6 of docs/02-detailed-design.md.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import psycopg
from fastapi import FastAPI

from common.clock import SystemClock
from common.consumer import ConsumerSettings, MessageConsumer
from common.kafka import Receiver, Sender
from common.outbox import OutboxRelay
from common.runtime import Workers, configure_logging, instance_name
from common.seed import load_menu
from common.service import identity
from common.topics import ORDER_EVENTS_PATTERN
from inventory_service.orders import Limits, make_order_created_handler
from inventory_service.stock import load_seed

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
            handlers={"OrderCreated": make_order_created_handler(clock, limits_from_env())},
            deciding=True,
        ),
        Receiver(bootstrap, CONSUMER_GROUP, [ORDER_EVENTS_PATTERN], f"{name}-consumer"),
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
