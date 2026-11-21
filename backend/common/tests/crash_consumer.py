"""Started as a separate process by test_consumer.py for scenario 26.

It consumes one message with the shared consumer and the same handler as the test, and stops
the process (os._exit, no clean-up) right after the DB commit of step 4 and before the offset
commit of step 5 in section 13.3 of docs/01-business-spec.md.

    python crash_consumer.py <bootstrap> <topic> <group> <dsn> <dlq topic>
"""

import os
import sys
import time
from typing import Any

import psycopg

from common.clock import SystemClock
from common.consumer import ConsumerSettings, Incoming, MessageConsumer
from common.envelope import new_envelope
from common.kafka import Receiver, Record, Sender
from common.outbox import enqueue

EXIT_CODE = 17


def reserve(conn: psycopg.Connection[Any], message: Incoming) -> None:
    """Stands in for Inventory's handler: one outbox row per order (the effect counted)."""
    env = message.envelope
    reply = new_envelope(
        "OrderReserved",
        order_id=env.order_id,
        branch_id="POS01",
        clock=SystemClock(),
        causation_id=env.event_id,
    )
    enqueue(conn, "status-events.POS01", reply)


def main() -> None:
    bootstrap, topic, group, dsn, dlq = sys.argv[1:6]

    def stop_here(_record: Record) -> None:
        os._exit(EXIT_CODE)

    consumer = MessageConsumer(
        ConsumerSettings(
            name="crash-consumer", handlers={"OrderCreated": reserve}, deciding=True, dlq_topic=dlq
        ),
        Receiver(bootstrap, group, [topic], "crash-consumer"),
        Sender(bootstrap, "crash-consumer"),
        lambda: psycopg.connect(dsn),
        after_db_commit=stop_here,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        consumer.poll_once(0.5)
    sys.exit("no message arrived within 60s")


if __name__ == "__main__":
    main()
