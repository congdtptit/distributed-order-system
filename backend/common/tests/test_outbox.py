"""Writing to the outbox of Inventory and the Kitchen (section 3 of docs/02-detailed-design.md).

Sending the rows to Kafka is tested against the real cluster in test_broker_down.py (tier 3).
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import psycopg
import psycopg.sql
import pytest

from common.alerts import NEEDS_REVIEW, write_alert
from common.clock import FixedClock
from common.envelope import new_envelope
from common.outbox import enqueue

CLOCK = FixedClock(datetime(2026, 11, 20, 9, 15, tzinfo=UTC))


@pytest.mark.parametrize("module", ["inventory-service", "kitchen-service"])
def test_enqueue_stores_the_whole_envelope_keyed_by_order_id(
    migrated: Callable[[str], str], module: str
) -> None:
    dsn = migrated(module)
    order_id = uuid.uuid4()
    env = new_envelope(
        "OrderFailed",
        order_id=order_id,
        branch_id="POS01",
        clock=CLOCK,
        payload={"origin_branch": "POS01", "reason_code": "THIEU_NGUYEN_LIEU"},
    )
    with psycopg.connect(dsn) as conn:
        enqueue(conn, "status-events.POS01", env)
        conn.commit()
        row = conn.execute(
            "SELECT event_id, topic, msg_key, payload, sent_at FROM outbox_events"
        ).fetchone()
    assert row is not None
    event_id, topic, key, payload, sent_at = row
    assert (event_id, topic, key, sent_at) == (
        env.event_id,
        "status-events.POS01",
        str(order_id),
        None,
    )
    assert payload == env.to_dict()


def test_enqueue_is_part_of_the_callers_transaction(migrated: Callable[[str], str]) -> None:
    dsn = migrated("inventory-service")
    env = new_envelope("OrderReserved", order_id=uuid.uuid4(), branch_id="POS01", clock=CLOCK)
    with psycopg.connect(dsn) as conn:
        enqueue(conn, "kitchen-orders", env)
        conn.rollback()
        assert _count(conn, "outbox_events") == 0


def test_a_message_without_an_order_needs_an_explicit_key(migrated: Callable[[str], str]) -> None:
    dsn = migrated("inventory-service")
    heartbeat = new_envelope("Heartbeat", order_id=None, branch_id=None, clock=CLOCK)
    with psycopg.connect(dsn) as conn:
        with pytest.raises(ValueError):
            enqueue(conn, "menu-events", heartbeat)
        enqueue(conn, "menu-events", heartbeat, key="heartbeat")
        conn.commit()
        assert conn.execute("SELECT msg_key FROM outbox_events").fetchone() == ("heartbeat",)


def test_the_same_message_raises_an_alert_once(migrated: Callable[[str], str]) -> None:
    dsn = migrated("kitchen-service")
    order_id = uuid.uuid4()
    with psycopg.connect(dsn) as conn:
        args: dict[str, Any] = {
            "order_id": order_id,
            "event_id": None,
            "source_topic": "kitchen-orders",
            "source_partition": 1,
            "source_offset": 42,
        }
        assert write_alert(conn, NEEDS_REVIEW, **args) is True
        assert write_alert(conn, NEEDS_REVIEW, **args) is False
        conn.commit()
        assert _count(conn, "alerts") == 1


def _count(conn: psycopg.Connection[Any], table: str) -> int:
    query = psycopg.sql.SQL("SELECT count(*) FROM {}").format(psycopg.sql.Identifier(table))
    row = conn.execute(query).fetchone()
    assert row is not None
    return int(row[0])
