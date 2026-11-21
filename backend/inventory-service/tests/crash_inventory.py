"""Started as a separate process by test_consumer_inventory.py for scenario 26.

Runs Inventory's real OrderCreated handler in the shared consumer and stops the process
(os._exit, no clean-up) right after the DB commit and before the offset commit.

    python crash_inventory.py <bootstrap> <topic> <group> <dsn> <dlq topic>
"""

import os
import sys
import time

import psycopg

from common.clock import SystemClock
from common.consumer import ConsumerSettings, MessageConsumer
from common.kafka import Receiver, Record, Sender
from inventory_service.orders import Limits, make_order_created_handler

EXIT_CODE = 17


def main() -> None:
    bootstrap, topic, group, dsn, dlq = sys.argv[1:6]

    def stop_here(_record: Record) -> None:
        os._exit(EXIT_CODE)

    consumer = MessageConsumer(
        ConsumerSettings(
            name="inventory-crash",
            handlers={"OrderCreated": make_order_created_handler(SystemClock(), Limits())},
            deciding=True,
            dlq_topic=dlq,
        ),
        Receiver(bootstrap, group, [topic], "inventory-crash"),
        Sender(bootstrap, "inventory-crash"),
        lambda: psycopg.connect(dsn),
        after_db_commit=stop_here,
        branch_of=lambda _topic: "POS01",
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        consumer.poll_once(0.5)
    sys.exit("no message arrived within 60s")


if __name__ == "__main__":
    main()
