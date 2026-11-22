"""Helpers shared by the branch tests: placing orders in a branch DB, delivering status messages
through the consumer's deduplication (``handle_once``), and readers of the branch DB."""

import itertools
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg

from common.clock import Clock, FixedClock
from common.consumer import Incoming, Source, handle_once
from common.envelope import Envelope, decode, new_envelope
from common.seed import load_menu
from common.topics import branch_from_topic, status_events
from order_service.orders import Line, cancel_order, create_order, load_dishes
from order_service.statuses import branch_handlers

NOW = datetime(2026, 11, 20, 9, 15, tzinfo=UTC)
BRANCH = "POS01"
_offsets = itertools.count()


def with_dishes(dsn: str) -> str:
    """Load the dish catalogue of backend/seed/menu.json, as the service does on start."""
    with psycopg.connect(dsn) as conn:
        load_dishes(conn, load_menu())
    return dsn


def place(
    dsn: str,
    lines: list[tuple[str, int]] | None = None,
    *,
    branch: str = BRANCH,
    clock: Clock | None = None,
) -> uuid.UUID:
    """``POST /orders`` without HTTP: one committed order and its create-order entry."""
    with psycopg.connect(dsn) as conn:
        order = create_order(
            conn,
            branch,
            [Line(d, q) for d, q in (lines or [("PHO_BO", 1)])],
            clock or FixedClock(NOW),
        )
        conn.commit()
    return order["order_id"]


def cancel(
    dsn: str, order_id: uuid.UUID, reason: str = "CHANGED_MIND", *, branch: str = BRANCH
) -> bool:
    """Write (2), committed. True for a local cancel."""
    with psycopg.connect(dsn) as conn:
        result = cancel_order(conn, branch, order_id, reason, FixedClock(NOW))
        conn.commit()
    return result.local


def mark_attempted(dsn: str, order_id: uuid.UUID, *, sent: bool = False) -> None:
    """The sender's write (1) on the order's create-order entry (and, if ``sent``, Kafka's
    acknowledgement), without Kafka."""
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE outbox_events SET attempted = TRUE, sent_at = CASE WHEN %s THEN %s END"
            " WHERE order_id = %s AND kind = 'TAO_DON'",
            (sent, NOW, order_id),
        )


def status_message(
    event_type: str,
    order_id: uuid.UUID | None,
    payload: dict[str, Any] | None = None,
    *,
    branch: str = BRANCH,
) -> Envelope:
    """A status message as Inventory or the Kitchen sends it (section 2 of document 02)."""
    return new_envelope(
        event_type, order_id=order_id, branch_id=branch, clock=FixedClock(NOW), payload=payload
    )


def deliver(
    dsn: str,
    env: Envelope,
    *,
    branch: str = BRANCH,
    topic: str | None = None,
    conn: psycopg.Connection[Any] | None = None,
) -> bool:
    """Process one message as the branch's consumer would (steps 1 to 4); False for a
    duplicate. The topic defaults to the branch's own ``status-events``."""
    topic = topic or status_events(branch)
    handler = branch_handlers(branch)[env.event_type]
    message = Incoming(env, branch_from_topic(topic), Source(topic, 0, next(_offsets)))
    if conn is not None:
        return handle_once(conn, handler, message)
    with psycopg.connect(dsn, autocommit=True) as own:
        return handle_once(own, handler, message)


def order_row(dsn: str, order_id: uuid.UUID | None) -> dict[str, Any] | None:
    with psycopg.connect(dsn) as conn:
        cur = conn.execute(
            "SELECT status, status_rank, close_reason, cancel_flag, cancel_message,"
            " cancel_requested_at FROM orders WHERE order_id = %s",
            (order_id,),
        )
        row = cur.fetchone()
        names = [d.name for d in cur.description or []]
    return None if row is None else dict(zip(names, row, strict=True))


def entries(dsn: str, order_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    """The send queue in ``id`` order (one order's entries, if given)."""
    with psycopg.connect(dsn) as conn:
        cur = conn.execute(
            "SELECT id, order_id, kind, topic, attempted, sent_at, payload FROM outbox_events"
            " WHERE %s::uuid IS NULL OR order_id = %s ORDER BY id",
            (order_id, order_id),
        )
        names = [d.name for d in cur.description or []]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def queued_envelope(dsn: str, order_id: uuid.UUID | None, kind: str = "TAO_DON") -> Envelope:
    """The message one of the order's entries will send, as the receiver decodes it: to hand
    the branch's real messages to Inventory's and the Kitchen's handlers."""
    [entry] = [e for e in entries(dsn, order_id) if e["kind"] == kind]
    return decode(json.dumps(entry["payload"]).encode())


def processed(dsn: str) -> set[uuid.UUID]:
    with psycopg.connect(dsn) as conn:
        return {r[0] for r in conn.execute("SELECT event_id FROM processed_events").fetchall()}
