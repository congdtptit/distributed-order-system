"""Scenario 31 against the running cluster (tier 3): one Kafka broker is shut down while orders
are being sent.

The sender is the outbox relay of Inventory and the Kitchen, with the producer settings of
section 13.1 of docs/01-business-spec.md (``acks=all``, ``enable.idempotence=true``) and the
topic settings (3 replicas, ``min.insync.replicas=2``). The branch's send queue uses the same
producer settings and gets its own sender in step 6.
"""

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, Protocol

import psycopg
import pytest

from common.clock import SystemClock
from common.envelope import decode, new_envelope
from common.kafka import Receiver, Sender, partition_leaders
from common.outbox import OutboxRelay, enqueue

pytestmark = pytest.mark.tier3

CLOCK = SystemClock()


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def kill(self, service: str) -> None: ...
    def health(self, service: str) -> str: ...


def write_orders(dsn: str, topic: str, n: int, written: list[uuid.UUID]) -> None:
    """``n`` orders arrive one by one; each is one outbox row in its own transaction."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        for _ in range(n):
            env = new_envelope(
                "OrderCreated", order_id=uuid.uuid4(), branch_id="POS01", clock=CLOCK
            )
            with conn.transaction():
                enqueue(conn, topic, env)
            written.append(env.event_id)
            time.sleep(0.02)


def outbox(dsn: str) -> list[tuple[Any, ...]]:
    """(id, event_id, sent_at) of every outbox row."""
    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT id, event_id, sent_at FROM outbox_events ORDER BY id"
        ).fetchall()


def wait_for(condition: Callable[[], bool], timeout_s: float, what: str) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.2)


@pytest.mark.kb(31)
def test_a_broker_shut_down_while_sending_loses_no_acknowledged_message(
    migrated: Callable[[str], str],
    new_topic: Callable[[int], str],
    kafka_bootstrap: str,
    chaos: Chaos,
) -> None:
    dsn = migrated("inventory-service")
    topic = new_topic(2)
    relay = OutboxRelay(
        lambda: psycopg.connect(dsn), Sender(kafka_bootstrap, "test-relay"), CLOCK, batch_size=20
    )
    stop = threading.Event()
    relay_thread = threading.Thread(target=relay.run, args=(stop,), daemon=True)
    relay_thread.start()
    written: list[uuid.UUID] = []
    # Orders arrive steadily for about 8 s, before, during and after the broker dies.
    writer = threading.Thread(target=write_orders, args=(dsn, topic, 400, written), daemon=True)
    try:
        writer.start()
        wait_for(lambda: sum(1 for r in outbox(dsn) if r[2] is not None) >= 50, 60, "50 rows sent")

        # Kill (SIGKILL, no clean hand-over) the broker that leads partition 0 while orders
        # are still being written and sent. Whether a batch is in flight at that instant is luck
        # (the relay keeps up with 50 rows a second), so the test asserts what the scenario
        # names: sending is under way when the broker dies.
        leader = partition_leaders(kafka_bootstrap, topic)[0]
        broker = f"kafka{leader}"
        assert writer.is_alive(), "orders stopped arriving before the broker died"
        chaos.kill(broker)
        last_id_at_kill = outbox(dsn)[-1][0]

        writer.join(timeout=60)
        assert not writer.is_alive()

        # Sending continues: every row is acknowledged with the broker still down.
        wait_for(lambda: all(r[2] is not None for r in outbox(dsn)), 120, "every row sent")
        assert chaos.health(broker) != "healthy"
        after_kill = [r for r in outbox(dsn) if r[0] > last_id_at_kill]
        assert len(after_kill) > 100, "too few orders were written after the kill"
        assert all(r[2] is not None for r in after_kill)
        # Partition 0 has a new leader among the brokers still running.
        assert partition_leaders(kafka_bootstrap, topic)[0] not in (leader, -1)
    finally:
        stop.set()
        relay_thread.join(timeout=60)

    # No message acknowledged by Kafka is lost: read back from the brokers still running.
    acknowledged = {r[1] for r in outbox(dsn) if r[2] is not None}
    assert acknowledged == set(written)
    received: set[uuid.UUID] = set()
    receiver = Receiver(kafka_bootstrap, f"reader-{uuid.uuid4().hex[:8]}", [topic], "reader")
    deadline = time.monotonic() + 60
    try:
        while not acknowledged <= received and time.monotonic() < deadline:
            record = receiver.poll(0.5)
            if record is not None:
                received.add(decode(record.value).event_id)
    finally:
        receiver.close()
    missing = acknowledged - received
    assert not missing, f"{len(missing)} acknowledged messages are missing from {topic}"
