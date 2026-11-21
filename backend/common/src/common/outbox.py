"""The outbox of Inventory and the Kitchen (table ``outbox_events``, section 3 of
docs/02-detailed-design.md) and its relay to Kafka.

A handler writes outgoing messages with ``enqueue`` inside its own DB transaction, so a message
exists exactly when the state change that caused it was committed. The relay sends unsent rows
and marks a row as sent only after Kafka acknowledged it (section 13.1 of the specification).
The ``payload`` column holds the whole envelope, which is the Kafka message value.

The branch's send queue is a different table with the "send attempted" flag (section 5 of
document 02) and gets its own sender in step 6.
"""

import json
import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from common.clock import Clock
from common.envelope import Envelope
from common.kafka import Outgoing, Sender

log = logging.getLogger(__name__)

Connect = Callable[[], psycopg.Connection[Any]]


def enqueue(
    conn: psycopg.Connection[Any], topic: str, envelope: Envelope, *, key: str | None = None
) -> None:
    """Add one message to the outbox in the caller's transaction.

    The key defaults to the order ID, the partition key of every order topic. Messages that
    belong to no order (``menu-events``) pass their key explicitly (section 2 of document 02).
    """
    if key is None:
        if envelope.order_id is None:
            raise ValueError(f"{envelope.event_type} has no order_id: pass the key explicitly")
        key = str(envelope.order_id)
    conn.execute(
        "INSERT INTO outbox_events (event_id, topic, msg_key, payload) VALUES (%s, %s, %s, %s)",
        (envelope.event_id, topic, key, Jsonb(envelope.to_dict())),
    )


class OutboxRelay:
    """Sends unsent outbox rows in ascending ``id``.

    Two instances of a service can run a relay each on the same DB: rows are claimed with
    FOR UPDATE SKIP LOCKED, so the instances never send the same row at the same time. The row
    lock is held while Kafka is asked, so a row is marked sent only after its acknowledgement.
    A row Kafka did not acknowledge stays unsent and is retried; it is never dropped.
    """

    def __init__(
        self, connect: Connect, sender: Sender, clock: Clock, *, batch_size: int = 100
    ) -> None:
        self._connect = connect
        self._sender = sender
        self._clock = clock
        self._batch_size = batch_size
        self._conn: psycopg.Connection[Any] | None = None

    def relay_once(self) -> int:
        """Send one batch. Returns the number of rows Kafka acknowledged."""
        conn = self._connection()
        with conn.transaction():
            rows = conn.execute(
                """
                SELECT id, event_id, topic, msg_key, payload FROM outbox_events
                 WHERE sent_at IS NULL
                 ORDER BY id
                 LIMIT %s
                 FOR UPDATE SKIP LOCKED
                """,
                (self._batch_size,),
            ).fetchall()
            if not rows:
                return 0
            acked = self._sender.send_all(
                [
                    Outgoing(
                        topic=str(topic),
                        key=str(key).encode(),
                        value=json.dumps(payload, ensure_ascii=False).encode(),
                    )
                    for _id, _event_id, topic, key, payload in rows
                ]
            )
            sent_ids = [row[0] for row, ok in zip(rows, acked, strict=True) if ok]
            if sent_ids:
                conn.execute(
                    "UPDATE outbox_events SET sent_at = %s WHERE id = ANY(%s)",
                    (self._clock.now(), sent_ids),
                )
        for row, ok in zip(rows, acked, strict=True):
            if not ok:
                log.warning(
                    "order_id=%s event_id=%s outbox: not acknowledged, will retry",
                    row[3],
                    uuid.UUID(str(row[1])),
                )
        return len(sent_ids)

    def run(self, stop: threading.Event, *, idle_s: float = 0.2) -> None:
        """Relay until ``stop`` is set. A DB error waits with growing backoff and reconnects."""
        backoff = 0.2
        while not stop.is_set():
            try:
                sent = self.relay_once()
                backoff = 0.2
            except psycopg.OperationalError as exc:
                log.warning("outbox: DB error, retrying in %.1fs: %s", backoff, exc)
                self._drop_connection()
                stop.wait(backoff)
                backoff = min(backoff * 2, 5.0)
                continue
            if sent == 0:
                stop.wait(idle_s)
        self._drop_connection()

    def _connection(self) -> psycopg.Connection[Any]:
        if self._conn is None or self._conn.closed:
            self._conn = self._connect()
            self._conn.autocommit = True
        return self._conn

    def _drop_connection(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None
