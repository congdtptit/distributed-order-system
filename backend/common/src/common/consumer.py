"""The consumer loop shared by every service.

Each message is processed in exactly the five steps of section 13.3 of
docs/01-business-spec.md:

1. open a DB transaction;
2. insert the ``event_id`` into ``processed_events``; if it is already there the message is a
   duplicate: roll back and go to step 5;
3. apply the state table (the service's handler);
4. write the outbox (the handler, in the same transaction), then commit;
5. commit the Kafka offset.

Bad messages follow the table "Handling bad messages and unknown events" in section 9:

- a transient error (lost DB connection, timeout, deadlock) is retried without limit, with
  growing backoff;
- any other error, an unreadable message included, is tried ``max_attempts`` times, then the
  message goes to the dlq and an alert is raised;
- an unknown ``event_type``, or a ``schema_version`` higher than this code supports, goes to the
  dlq at once on a deciding side (Inventory, the Kitchen) and is logged, alerted and skipped on
  a display-only side (the branches);
- a type in the catalogue that is not meant for this service is skipped: no
  ``processed_events`` row, no dlq (section 2 of docs/02-detailed-design.md).

A message going to the dlq is sent directly, not through the outbox: send it and wait for the
acknowledgement, write the ``alerts`` row, and only then commit the offset. The dlq message
keeps the original key and value and gains headers naming where it came from.

The handler receives one message and one open transaction and knows nothing about Kafka.
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import psycopg
from confluent_kafka import KafkaError, KafkaException

from common.alerts import NEEDS_REVIEW, write_alert
from common.envelope import (
    EVENT_TYPES,
    SCHEMA_VERSION,
    Envelope,
    UnreadableMessage,
    decode,
    uuid_or_none,
)
from common.kafka import Outgoing, Receiver, Record, Sender, SendError
from common.topics import DLQ, branch_from_topic

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    """Where a message was read: the key of an ``alerts`` row (section 3 of document 02)."""

    topic: str
    partition: int
    offset: int


@dataclass(frozen=True)
class Incoming:
    """What a handler gets: the message, the sending branch taken from the topic name, and
    where the message was read (for alerts only; the handler never talks to Kafka)."""

    envelope: Envelope
    source_branch: str | None
    source: Source | None = None


Handler = Callable[[psycopg.Connection[Any], Incoming], None]
Connect = Callable[[], psycopg.Connection[Any]]


class Outcome(StrEnum):
    HANDLED = "handled"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"
    """A known type that is not meant for this service."""
    DEAD_LETTERED = "dead_lettered"
    IGNORED_UNKNOWN = "ignored_unknown"
    """Display-only side: an unknown type, logged and alerted."""


@dataclass(frozen=True)
class ConsumerSettings:
    name: str
    """The consumer's name, written into the dlq headers and the alert detail."""
    handlers: Mapping[str, Handler]
    """event_type -> handler, for the types meant for this service."""
    deciding: bool
    """True for Inventory and the Kitchen, False for the branches (section 9)."""
    alerts_table: bool = True
    """Write alerts to the ``alerts`` table; False logs them (the branch DB has no such table)."""
    max_attempts: int = 5
    """Section 10 of the specification: attempts for a permanently failing message."""
    dlq_topic: str = DLQ
    backoff_s: float = 0.2
    max_backoff_s: float = 5.0


class _DeadLetter(Exception):
    pass


def handle_once(conn: psycopg.Connection[Any], handler: Handler, message: Incoming) -> bool:
    """Steps 1 to 4 of section 13.3 on an autocommit connection: one transaction that records
    the ``event_id`` and runs the handler. False if the ``event_id`` was already processed (the
    transaction is rolled back and the handler does not run).

    The consumer calls this for every message; handler-level tests call it directly, so they
    run the same deduplication as the consumer without Kafka.
    """
    duplicate = False
    with conn.transaction():  # step 1
        inserted = conn.execute(  # step 2
            "INSERT INTO processed_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (message.envelope.event_id,),
        ).rowcount
        if inserted == 0:
            duplicate = True
            raise psycopg.Rollback()
        handler(conn, message)  # steps 3 and 4
    return not duplicate


class MessageConsumer:
    def __init__(
        self,
        settings: ConsumerSettings,
        receiver: Receiver,
        dlq_sender: Sender,
        connect: Connect,
        *,
        after_db_commit: Callable[[Record], None] | None = None,
        branch_of: Callable[[str], str | None] = branch_from_topic,
    ) -> None:
        """``after_db_commit`` runs between steps 4 and 5; tests use it to stop the process
        there (scenario 26). ``branch_of`` maps a topic to the sending branch; tests on
        throwaway topics replace it, so that no service's ``order-events.*`` pattern sees them."""
        self.settings = settings
        self._receiver = receiver
        self._dlq = dlq_sender
        self._connect = connect
        self._after_db_commit = after_db_commit
        self._branch_of = branch_of
        self._conn: psycopg.Connection[Any] | None = None

    # ---------- the loop ----------

    def run(self, stop: threading.Event, *, poll_s: float = 0.5) -> None:
        backoff = self.settings.backoff_s
        try:
            while not stop.is_set():
                try:
                    self.poll_once(poll_s)
                    backoff = self.settings.backoff_s
                except KafkaException as exc:
                    if _is_fatal(exc):
                        raise
                    log.warning("%s: Kafka error, continuing: %s", self.settings.name, exc)
                    stop.wait(backoff)
                    backoff = min(backoff * 2, self.settings.max_backoff_s)
        finally:
            self.close()

    def poll_once(self, timeout_s: float) -> tuple[Record, Outcome] | None:
        record = self._receiver.poll(timeout_s)
        if record is None:
            return None
        try:
            return record, self.process(record)
        except BaseException:
            # The message did not finish its five steps. Move the fetch position back to it so
            # that it is read again instead of being passed over without a trace (section 9:
            # never ignored silently). If its DB commit did happen, step 2 blocks the repeat.
            order_id, _ = _identify(record)
            log.warning("order_id=%s not finished, will be read again", order_id)
            self._receiver.seek(record)
            raise

    def process(self, record: Record) -> Outcome:
        outcome = self._process_with_retries(record)
        self._receiver.commit(record)  # step 5
        order_id, event_id = _identify(record)
        log.info(
            "order_id=%s event_id=%s %s %s[%d]@%d",
            order_id,
            event_id,
            outcome,
            record.topic,
            record.partition,
            record.offset,
        )
        return outcome

    def close(self) -> None:
        try:
            self._receiver.close()
        finally:
            self._drop_connection()

    # ---------- one message ----------

    def _process_with_retries(self, record: Record) -> Outcome:
        attempts = 0
        backoff = self.settings.backoff_s
        while True:
            try:
                return self._process(record)
            except _DeadLetter as exc:
                self._dead_letter(record, str(exc))
                return Outcome.DEAD_LETTERED
            except psycopg.OperationalError as exc:
                order_id, _ = _identify(record)
                log.warning("order_id=%s transient DB error, retrying: %s", order_id, exc)
                self._drop_connection()
            except Exception as exc:
                attempts += 1
                order_id, _ = _identify(record)
                log.warning(
                    "order_id=%s attempt %d/%d failed: %s: %s",
                    order_id,
                    attempts,
                    self.settings.max_attempts,
                    type(exc).__name__,
                    exc,
                )
                if attempts >= self.settings.max_attempts:
                    self._dead_letter(record, f"{type(exc).__name__}: {exc}")
                    return Outcome.DEAD_LETTERED
            time.sleep(backoff)
            backoff = min(backoff * 2, self.settings.max_backoff_s)

    def _process(self, record: Record) -> Outcome:
        envelope = decode(record.value)  # UnreadableMessage counts as a failed attempt

        unknown = _unknown_reason(envelope)
        if unknown is not None:
            if self.settings.deciding:
                raise _DeadLetter(unknown)
            self._alert(record, unknown)
            return Outcome.IGNORED_UNKNOWN

        handler = self.settings.handlers.get(envelope.event_type)
        if handler is None:
            return Outcome.SKIPPED

        conn = self._connection()
        source = Source(record.topic, record.partition, record.offset)
        incoming = Incoming(envelope, self._branch_of(record.topic), source)
        if not handle_once(conn, handler, incoming):
            return Outcome.DUPLICATE
        if self._after_db_commit is not None:
            self._after_db_commit(record)
        return Outcome.HANDLED

    # ---------- dlq and alerts ----------

    def _dead_letter(self, record: Record, reason: str) -> None:
        message = Outgoing(
            topic=self.settings.dlq_topic,
            key=record.key,
            value=record.value,
            headers=(
                ("original_topic", record.topic.encode()),
                ("original_partition", str(record.partition).encode()),
                ("original_offset", str(record.offset).encode()),
                ("consumer", self.settings.name.encode()),
                ("error", reason[:1000].encode()),
            ),
        )
        backoff = self.settings.backoff_s
        while True:
            try:
                self._dlq.send_one(message)
                break
            except (SendError, KafkaException, BufferError) as exc:
                order_id, _ = _identify(record)
                log.warning("order_id=%s dlq send failed, retrying: %s", order_id, exc)
                time.sleep(backoff)
                backoff = min(backoff * 2, self.settings.max_backoff_s)
        self._alert(record, reason)

    def _alert(self, record: Record, reason: str) -> None:
        """Raise a "needs review" alert for the message (Flow D)."""
        order_id, event_id = _identify(record)
        detail: dict[str, Any] = {"error": reason[:1000], "consumer": self.settings.name}
        if not self.settings.alerts_table:
            log.error(
                "ALERT %s order_id=%s event_id=%s %s[%d]@%d: %s",
                NEEDS_REVIEW,
                order_id,
                event_id,
                record.topic,
                record.partition,
                record.offset,
                reason,
            )
            return
        backoff = self.settings.backoff_s
        while True:
            try:
                conn = self._connection()
                with conn.transaction():
                    write_alert(
                        conn,
                        NEEDS_REVIEW,
                        order_id=order_id,
                        event_id=event_id,
                        source_topic=record.topic,
                        source_partition=record.partition,
                        source_offset=record.offset,
                        detail=detail,
                    )
                return
            except psycopg.OperationalError as exc:
                log.warning("order_id=%s alert not written, retrying: %s", order_id, exc)
                self._drop_connection()
                time.sleep(backoff)
                backoff = min(backoff * 2, self.settings.max_backoff_s)

    # ---------- DB connection ----------

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


def _is_fatal(exc: KafkaException) -> bool:
    err = exc.args[0] if exc.args else None
    return isinstance(err, KafkaError) and err.fatal()


def _unknown_reason(envelope: Envelope) -> str | None:
    if envelope.event_type not in EVENT_TYPES:
        return f"unknown event_type {envelope.event_type!r}"
    if envelope.schema_version > SCHEMA_VERSION:
        return f"schema_version {envelope.schema_version} is higher than {SCHEMA_VERSION}"
    return None


def _identify(record: Record) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """(order_id, event_id) of a message, as far as it can be read. For an unreadable message
    the order ID is the Kafka key when the key is a UUID (section 3 of document 02)."""
    try:
        envelope = decode(record.value)
    except UnreadableMessage:
        return uuid_or_none(record.key), None
    return envelope.order_id or uuid_or_none(record.key), envelope.event_id
