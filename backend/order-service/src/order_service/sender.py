"""The branch's sender: it moves the send queue (``outbox_events`` of the branch DB) to Kafka.

BR5 and BR9 of docs/01-business-spec.md; write (1) and the notes after it in section 5 of
docs/02-detailed-design.md:

- Only the unsent entry with the smallest ``id`` of each order is a candidate, so a cancel
  entry never leaves before the create-order entry of the same order, while other orders are
  not held up.
- Before an entry without the flag is sent, the connection to Kafka is probed. Only if the
  probe has just succeeded does write (1) set ``attempted`` and commit; the send comes after.
  A failed probe leaves the entry unattempted, so it can still be cancelled locally
  (scenario 10). Write (1) finding no row means a local cancel discarded the entry: skip it.
- An entry with the flag is resent without probing, until Kafka acknowledges it. It is never
  dropped, whatever the error (scenario 12).
- The result of the most recent probe is the connection status of ``GET /monitor``.

One sender runs per branch; nothing else sets ``sent_at``, which is what keeps a cancel entry
behind its create-order entry.
"""

import json
import logging
import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import psycopg
from confluent_kafka import KafkaException

from common.clock import Clock
from common.kafka import Outgoing

log = logging.getLogger(__name__)

Connect = Callable[[], psycopg.Connection[Any]]


class Link(Protocol):
    """What the sender needs from Kafka: ``common.kafka.Sender``."""

    def probe(self, timeout_s: float = 2.0) -> bool: ...
    def send_all(self, messages: Sequence[Outgoing]) -> list[bool]: ...


@dataclass(frozen=True)
class ConnectionStatus:
    connected: bool | None
    """The result of the most recent probe; None before the first one."""
    checked_at: datetime | None


UNKNOWN = ConnectionStatus(None, None)


@dataclass(frozen=True)
class Entry:
    id: int
    event_id: uuid.UUID
    order_id: uuid.UUID
    topic: str
    payload: dict[str, Any]
    attempted: bool


@dataclass(frozen=True)
class Round:
    sent: int
    """Entries Kafka acknowledged."""
    failed: int
    """Entries sent but not acknowledged; they keep the flag and go again."""
    held: int
    """Entries without the flag left unattempted because the probe failed."""


class SendQueue:
    def __init__(
        self,
        connect: Connect,
        link: Link,
        clock: Clock,
        *,
        batch_size: int = 100,
        probe_timeout_s: float = 2.0,
        probe_every_s: float = 5.0,
    ) -> None:
        """``probe_every_s``: with nothing new to attempt, the connection is still probed this
        often, so that the status on ``GET /monitor`` stays current."""
        self._connect = connect
        self._link = link
        self._clock = clock
        self._batch_size = batch_size
        self._probe_timeout_s = probe_timeout_s
        self._probe_every_s = probe_every_s
        self._conn: psycopg.Connection[Any] | None = None
        self._status = UNKNOWN

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    def probe(self) -> bool:
        connected = self._link.probe(self._probe_timeout_s)
        if connected != self._status.connected:
            log.info("send queue: Kafka %s", "reachable" if connected else "unreachable")
        self._status = ConnectionStatus(connected, self._clock.now())
        return connected

    def send_once(self) -> Round:
        conn = self._connection()
        heads = self._heads(conn)
        fresh = [e.id for e in heads if not e.attempted]
        if fresh or self._probe_due():
            self.probe()
        started: set[int] = set()
        if fresh and self._status.connected:
            started = self.start_attempts(conn, fresh)
        to_send = [e for e in heads if e.attempted or e.id in started]
        held = 0 if self._status.connected else len(fresh)
        if not to_send:
            return Round(sent=0, failed=0, held=held)

        acked = self._link.send_all(
            [
                Outgoing(
                    topic=e.topic,
                    key=str(e.order_id).encode(),
                    value=json.dumps(e.payload, ensure_ascii=False).encode(),
                )
                for e in to_send
            ]
        )
        sent_ids = [e.id for e, ok in zip(to_send, acked, strict=True) if ok]
        if sent_ids:
            with conn.transaction():
                conn.execute(
                    "UPDATE outbox_events SET sent_at = %s WHERE id = ANY(%s)",
                    (self._clock.now(), sent_ids),
                )
        for e, ok in zip(to_send, acked, strict=True):
            if not ok:
                log.warning(
                    "order_id=%s event_id=%s not acknowledged, will retry", e.order_id, e.event_id
                )
        return Round(sent=len(sent_ids), failed=len(to_send) - len(sent_ids), held=held)

    def start_attempts(self, conn: psycopg.Connection[Any], ids: Sequence[int]) -> set[int]:
        """Write (1) for each entry, committed before anything is sent. Returns the entries
        that now carry the flag; an entry a local cancel already discarded is not among them."""
        with conn.transaction():
            rows = conn.execute(
                "UPDATE outbox_events SET attempted = TRUE"
                " WHERE id = ANY(%s) AND sent_at IS NULL RETURNING id",
                (list(ids),),
            ).fetchall()
        return {int(r[0]) for r in rows}

    def run(
        self,
        stop: threading.Event,
        *,
        idle_s: float = 0.2,
        backoff_s: float = 0.5,
        max_backoff_s: float = 5.0,
    ) -> None:
        """Send until ``stop`` is set. A failed send, an unreachable Kafka, a DB error or any
        other error waits with growing backoff (BR9) and tries again."""
        backoff = backoff_s
        while not stop.is_set():
            try:
                result = self.send_once()
            except psycopg.OperationalError as exc:
                log.warning("send queue: DB error, retrying in %.1fs: %s", backoff, exc)
                self._drop_connection()
                result = None
            except (KafkaException, BufferError) as exc:
                log.warning("send queue: Kafka error, retrying in %.1fs: %s", backoff, exc)
                result = None
            except Exception:
                # Anything else must not end the thread: the API would keep taking orders
                # that never leave the branch (BR9: retried, never discarded).
                log.exception("send queue: unexpected error, retrying in %.1fs", backoff)
                self._drop_connection()
                result = None
            if result is None or result.failed or result.held:
                stop.wait(backoff)
                backoff = min(backoff * 2, max_backoff_s)
                continue
            backoff = backoff_s
            if result.sent == 0:
                stop.wait(idle_s)
        self._drop_connection()

    # ---------- internals ----------

    def _heads(self, conn: psycopg.Connection[Any]) -> list[Entry]:
        """The unsent entry with the smallest ``id`` of each order, oldest first."""
        rows = conn.execute(
            """
            SELECT id, event_id, order_id, topic, payload, attempted FROM (
                SELECT DISTINCT ON (order_id) id, event_id, order_id, topic, payload, attempted
                  FROM outbox_events
                 WHERE sent_at IS NULL
                 ORDER BY order_id, id
            ) heads
            ORDER BY id
            LIMIT %s
            """,
            (self._batch_size,),
        ).fetchall()
        return [Entry(int(r[0]), r[1], r[2], str(r[3]), dict(r[4]), bool(r[5])) for r in rows]

    def _probe_due(self) -> bool:
        checked = self._status.checked_at
        return checked is None or (self._clock.now() - checked).total_seconds() >= (
            self._probe_every_s
        )

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
