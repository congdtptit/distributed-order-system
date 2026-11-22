"""Scenario 42 with two real Inventory instances (tier 3): ``inventory-1`` and ``inventory-2`` of
the compose cluster share the consumer group, so Kafka gives each of them one of the two
partitions of ``order-events.POS01``. Two orders whose ids fall into different partitions are
sent together; both need the one ingredient that has room for only one of them.

The handler-level race is test_reserve_race.py (tier 2, 100 runs). This version checks what
point 6 in section 8 of docs/02-detailed-design.md left to a trial run: that the two instances
each process one order, read from their logs. Needs ``docker compose --profile full``.
"""

import re
import time
import urllib.request
import uuid
import zlib
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg
import pytest
from inventory_support import D, order_created

from common.envelope import encode
from common.kafka import Outgoing, Sender
from inventory_service.invariants import violations
from inventory_service.stock import receive_stock

pytestmark = pytest.mark.tier3

INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
INSTANCES = ("inventory-1", "inventory-2")
TOPIC = "order-events.POS01"
PARTITIONS = 2
ROUNDS = 5


class Docker(Protocol):
    """The ``chaos`` fixture of backend/conftest.py, used here only to read logs."""

    def logs(self, service: str, since: float) -> str: ...


def partition_of(order_id: uuid.UUID) -> int:
    """Where librdkafka's default partitioner (consistent_random: CRC32 of the key) puts it."""
    return zlib.crc32(str(order_id).encode()) % PARTITIONS


def one_per_partition() -> list[uuid.UUID]:
    found: dict[int, uuid.UUID] = {}
    while len(found) < PARTITIONS:
        candidate = uuid.uuid4()
        found.setdefault(partition_of(candidate), candidate)
    return [found[p] for p in range(PARTITIONS)]


def decided(order_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    with psycopg.connect(INVENTORY_DB) as conn:
        rows = conn.execute(
            "SELECT order_id, status FROM inventory_orders WHERE order_id = ANY(%s)",
            (order_ids,),
        ).fetchall()
    return {r[0]: str(r[1]) for r in rows}


def reserved_lines(order_id: uuid.UUID) -> list[tuple[Any, ...]]:
    """Every reservation line of an order (a Failed order must have none)."""
    with psycopg.connect(INVENTORY_DB) as conn:
        return conn.execute(
            "SELECT ingredient_id, quantity FROM inventory_reservations WHERE order_id = %s",
            (order_id,),
        ).fetchall()


def available(ingredient_id: str) -> Any:
    with psycopg.connect(INVENTORY_DB) as conn:
        row = conn.execute(
            "SELECT available FROM stock WHERE ingredient_id = %s", (ingredient_id,)
        ).fetchone()
    assert row is not None
    return row[0]


def handled_by(docker: Docker, since: float, order_id: uuid.UUID) -> dict[str, int]:
    """Which instance logged handling the order's OrderCreated, and from which partition."""
    pattern = re.compile(rf"order_id={order_id} .* {re.escape(TOPIC)}\[(\d)\]@")
    found: dict[str, int] = {}
    for instance in INSTANCES:
        for line in docker.logs(instance, since).splitlines():
            m = pattern.search(line)
            if m:
                found[instance] = int(m.group(1))
    return found


@pytest.mark.kb(42)
def test_two_instances_each_take_one_order_and_exactly_one_is_reserved(
    chaos: Docker, kafka_bootstrap: str
) -> None:
    """Scenario 42: two orders arrive at the same time at two Inventory instances, both needing
    the same ingredient, with total demand exceeding available stock. Exactly one order is
    Reserved and the other is Failed; available stock is not negative; no order is partially
    reserved."""
    for instance in INSTANCES:
        with urllib.request.urlopen(f"http://{instance}:8000/health", timeout=5) as r:
            assert r.status == 200, f"{instance}: docker compose --profile full up -d"
    sender = Sender(kafka_bootstrap, "test-scenario-42")
    with psycopg.connect(INVENTORY_DB) as conn:
        before = conn.execute(
            "SELECT available FROM stock WHERE ingredient_id = 'THIT_LON'"
        ).fetchone()
    assert before is not None
    try:
        for _ in range(ROUNDS):
            # BUN_CHA needs BUN 0.2, THIT_LON 0.15, RAU_SONG 0.05: room for one order only,
            # because of THIT_LON; the other two have plenty.
            with psycopg.connect(INVENTORY_DB) as conn:
                for ingredient in ("BUN", "RAU_SONG"):
                    assert receive_stock(conn, ingredient, D("1"))
                conn.execute("UPDATE stock SET available = 0.2 WHERE ingredient_id = 'THIT_LON'")
            order_ids = one_per_partition()
            since = time.time() - 1
            envs = [
                order_created(order_id=o, created_at=datetime.now(UTC), items=[("BUN_CHA", 1)])
                for o in order_ids
            ]
            acked = sender.send_all(
                [Outgoing(TOPIC, str(e.order_id).encode(), encode(e)) for e in envs]
            )
            assert acked == [True, True]

            deadline = time.monotonic() + 60
            while len(statuses := decided(order_ids)) < 2:
                assert time.monotonic() < deadline, f"undecided: {statuses}"
                time.sleep(0.2)
            # Exactly one order is Reserved and the other is Failed.
            assert sorted(statuses.values()) == ["DANG_GIU", "THAT_BAI"], statuses
            [failed] = [o for o, s in statuses.items() if s == "THAT_BAI"]
            # No order is partially reserved.
            assert reserved_lines(failed) == []
            # Available stock is not negative (0.2 - 0.15), and the books balance.
            assert available("THIT_LON") == D("0.05")
            with psycopg.connect(INVENTORY_DB) as conn:
                assert violations(conn) == {}

            # The two instances each processed one order, from its own partition.
            logged: list[dict[str, int]] = []
            log_deadline = time.monotonic() + 10
            while time.monotonic() < log_deadline:
                logged = [handled_by(chaos, since, o) for o in order_ids]
                if all(logged):
                    break
                time.sleep(0.5)
            assert [list(by.values()) for by in logged] == [[0], [1]], logged
            assert len({next(iter(by)) for by in logged}) == 2, logged
    finally:
        with psycopg.connect(INVENTORY_DB) as conn:
            conn.execute(
                "UPDATE stock SET available = GREATEST(available, %s) "
                "WHERE ingredient_id = 'THIT_LON'",
                (before[0],),
            )
