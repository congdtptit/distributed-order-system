"""The only module that talks to confluent-kafka.

The configuration that section 13.1 of docs/01-business-spec.md makes mandatory lives here:
the producer uses ``acks=all`` and ``enable.idempotence=true``; the consumer turns offset
auto-commit off (section 13.3) and commits each message's offset itself.
"""

import logging
import re
import time
from collections.abc import Sequence
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from confluent_kafka import Consumer, KafkaError, KafkaException, Message, Producer, TopicPartition
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

log = logging.getLogger(__name__)

DELIVERY_TIMEOUT_S = 30.0
"""How long the producer keeps retrying one message before it reports the message as failed."""


@dataclass(frozen=True)
class Record:
    """One message read from Kafka, detached from the client library."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None
    headers: tuple[tuple[str, bytes], ...] = ()


@dataclass(frozen=True)
class Outgoing:
    topic: str
    key: bytes | None
    value: bytes | None
    headers: tuple[tuple[str, bytes], ...] = field(default=())


class SendError(Exception):
    """Kafka did not acknowledge a message."""


def producer_config(
    bootstrap: str, client_id: str, *, delivery_timeout_s: float = DELIVERY_TIMEOUT_S
) -> dict[str, str | int | float | bool]:
    return {
        "bootstrap.servers": bootstrap,
        "client.id": client_id,
        "acks": "all",
        "enable.idempotence": True,
        "message.timeout.ms": int(delivery_timeout_s * 1000),
        "linger.ms": 5,
    }


def consumer_config(
    bootstrap: str, group_id: str, client_id: str
) -> dict[str, str | int | float | bool]:
    return {
        "bootstrap.servers": bootstrap,
        "group.id": group_id,
        "client.id": client_id,
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        # A crashed member holds its partitions until this expires (default 45 s); 10 s keeps
        # a stopped instance's orders from waiting long (scenarios 26, 28, 42).
        "session.timeout.ms": 10_000,
        "heartbeat.interval.ms": 3_000,
        # A pattern subscription (order-events.*) sees a new branch's topic within 30 s.
        "topic.metadata.refresh.interval.ms": 30_000,
    }


class Sender:
    """A producer that reports, for each message, whether Kafka acknowledged it."""

    def __init__(
        self, bootstrap: str, client_id: str, *, delivery_timeout_s: float = DELIVERY_TIMEOUT_S
    ) -> None:
        """``delivery_timeout_s``: after this long a message counts as failed; tests that cut
        the connection shorten it so that a failed attempt does not take 30 s."""
        self._delivery_timeout_s = delivery_timeout_s
        self._producer = Producer(
            producer_config(bootstrap, client_id, delivery_timeout_s=delivery_timeout_s)
        )

    def probe(self, timeout_s: float = 2.0) -> bool:
        """The connectivity probe of section 5 of docs/02-detailed-design.md: True if a broker
        answered a cluster metadata request within ``timeout_s``."""
        try:
            metadata = self._producer.list_topics(timeout=timeout_s)
        except KafkaException:
            return False
        return bool(metadata.brokers)

    def send_all(self, messages: Sequence[Outgoing]) -> list[bool]:
        """Send and wait. Element i is True only if Kafka acknowledged message i."""
        acked = [False] * len(messages)

        def on_delivery(index: int):
            def callback(err: KafkaError | None, msg: Message) -> None:
                if err is None:
                    acked[index] = True
                else:
                    key = msg.key()
                    order = key.decode(errors="replace") if isinstance(key, bytes) else key
                    log.warning("order_id=%s send to %s failed: %s", order, msg.topic(), err)

            return callback

        for i, m in enumerate(messages):
            while True:
                try:
                    self._producer.produce(
                        m.topic,
                        value=m.value,
                        key=m.key,
                        headers=list(m.headers),
                        on_delivery=on_delivery(i),
                    )
                    break
                except BufferError:
                    self._producer.poll(0.5)  # local queue full: let deliveries drain
                except KafkaException as exc:
                    # Refused before sending (too large, an invalid topic name): this message
                    # fails, the others in the batch still go (section 9: one failing entry
                    # does not block the send queue).
                    key = m.key.decode(errors="replace") if m.key else None
                    log.warning("order_id=%s send to %s refused: %s", key, m.topic, exc)
                    break
        # Every message ends within message.timeout.ms, acknowledged or failed.
        self._producer.flush(self._delivery_timeout_s + 10)
        return acked

    def send_one(self, message: Outgoing) -> None:
        if not self.send_all([message])[0]:
            raise SendError(f"Kafka did not acknowledge the message to {message.topic}")


class Receiver:
    """A consumer in a group, with offset auto-commit off."""

    def __init__(self, bootstrap: str, group_id: str, topics: Sequence[str], client_id: str):
        """``topics`` may hold patterns starting with ``^``, e.g. ``^order-events\\..*``."""
        self._consumer = Consumer(consumer_config(bootstrap, group_id, client_id))
        self._consumer.subscribe(list(topics))

    def poll(self, timeout_s: float) -> Record | None:
        msg = self._consumer.poll(timeout_s)
        if msg is None:
            return None
        err = msg.error()
        if err is not None:
            if err.fatal():
                raise KafkaException(err)
            log.warning("consumer: %s", err)
            return None
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()
        assert topic is not None and partition is not None and offset is not None
        key = msg.key()
        value = msg.value()
        raw_headers = msg.headers() or []
        return Record(
            topic=topic,
            partition=partition,
            offset=offset,
            key=key.encode() if isinstance(key, str) else key,
            value=value.encode() if isinstance(value, str) else value,
            headers=tuple(
                (k, v.encode() if isinstance(v, str) else (v or b"")) for k, v in raw_headers
            ),
        )

    def seek(self, record: Record) -> None:
        """Read ``record`` again on the next poll."""
        self._consumer.seek(TopicPartition(record.topic, record.partition, record.offset))

    def commit(self, record: Record) -> None:
        """Commit the offset after ``record`` and wait for the broker (step 5 of section 13.3)."""
        self._consumer.commit(
            offsets=[TopicPartition(record.topic, record.partition, record.offset + 1)],
            asynchronous=False,
        )

    def close(self) -> None:
        """Leave the group. Offsets are not committed: auto-commit is off."""
        self._consumer.close()


# ---------- administration: topic setup and inspection (scripts and tier 3 tests) ----------


def create_topic(bootstrap: str, name: str, partitions: int, *, timeout_s: float = 30) -> None:
    """Create a topic with the mandatory settings of section 13.1 of the specification."""
    admin = AdminClient({"bootstrap.servers": bootstrap})
    topic = NewTopic(
        name,
        num_partitions=partitions,
        replication_factor=3,
        config={"min.insync.replicas": "2", "retention.ms": str(7 * 24 * 3600 * 1000)},
    )
    futures = cast(dict[str, Future[Any]], admin.create_topics([topic]))  # pyright: ignore[reportUnknownMemberType]
    futures[name].result(timeout_s)
    # Metadata reaches every broker a moment after creation.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        meta = admin.list_topics(name, timeout=5).topics.get(name)
        if (
            meta is not None
            and meta.error is None
            and len(meta.partitions) == partitions
            and all(p.leader >= 0 for p in meta.partitions.values())
        ):
            return
        time.sleep(0.2)
    raise TimeoutError(f"topic {name} has no leaders after {timeout_s}s")


def delete_topics(bootstrap: str, names: Sequence[str]) -> None:
    if names:
        admin = AdminClient({"bootstrap.servers": bootstrap})
        futures = cast(dict[str, Future[Any]], admin.delete_topics(list(names)))  # pyright: ignore[reportUnknownMemberType]
        for future in futures.values():
            future.result(30)


def partition_leaders(bootstrap: str, topic: str) -> dict[int, int]:
    """Partition -> node ID of its leader broker (kafka<N> in docker/kafka.yml has node ID N)."""
    admin = AdminClient({"bootstrap.servers": bootstrap})
    meta = admin.list_topics(topic, timeout=10).topics[topic]
    return {p.id: p.leader for p in meta.partitions.values()}


def partition_owners(bootstrap: str, group_id: str, topic: str) -> dict[int, str]:
    """Partition -> member id of the group member that holds it right now (tier 3 tests)."""
    admin = AdminClient({"bootstrap.servers": bootstrap})
    futures = cast(
        dict[str, Any],
        admin.describe_consumer_groups([group_id]),  # pyright: ignore[reportUnknownMemberType]
    )
    group: Any = futures[group_id].result(timeout=10)
    owners: dict[int, str] = {}
    for member in group.members:
        assignment: Any = member.assignment
        held = cast(list[TopicPartition], assignment.topic_partitions if assignment else [])
        for tp in held:
            if tp.topic == topic:
                owners[tp.partition] = str(member.member_id)
    return owners


class TopicTail:
    """Reads what is written to some topics from the moment it is created, without a consumer
    group (no offsets committed). For end-to-end tests on the shared topics."""

    def __init__(self, bootstrap: str, topics: Sequence[str]) -> None:
        self._consumer = Consumer(consumer_config(bootstrap, "tail", "tail"))
        assignment: list[TopicPartition] = []
        meta = self._consumer.list_topics(timeout=10)
        for topic in topics:
            for partition in meta.topics[topic].partitions:
                _low, high = self._consumer.get_watermark_offsets(
                    TopicPartition(topic, partition), timeout=10
                )
                assignment.append(TopicPartition(topic, partition, high))
        self._consumer.assign(assignment)

    def read(self, seconds: float) -> list[Record]:
        """Everything that arrives within ``seconds``."""
        records: list[Record] = []
        deadline = time.monotonic() + seconds
        while (left := deadline - time.monotonic()) > 0:
            msg = self._consumer.poll(min(left, 0.5))
            if msg is None or msg.error() is not None:
                continue
            topic, partition, offset = msg.topic(), msg.partition(), msg.offset()
            assert topic is not None and partition is not None and offset is not None
            key, value = msg.key(), msg.value()
            records.append(
                Record(
                    topic=topic,
                    partition=partition,
                    offset=offset,
                    key=key.encode() if isinstance(key, str) else key,
                    value=value.encode() if isinstance(value, str) else value,
                )
            )
        return records

    def close(self) -> None:
        self._consumer.close()


def end_offset(bootstrap: str, topic: str, partition: int) -> int:
    """The offset the next message written to the partition will get."""
    consumer = Consumer(consumer_config(bootstrap, "inspect-watermarks", "inspect-watermarks"))
    try:
        _low, high = consumer.get_watermark_offsets(TopicPartition(topic, partition), timeout=10)
        return high
    finally:
        consumer.close()


def committed_offset(bootstrap: str, group_id: str, topic: str, partition: int) -> int | None:
    """The offset a consumer group has committed for one partition, None if nothing yet."""
    consumer = Consumer(consumer_config(bootstrap, group_id, f"{group_id}-inspect"))
    try:
        [tp] = consumer.committed([TopicPartition(topic, partition)], timeout=10)
        return tp.offset if tp.offset >= 0 else None
    finally:
        consumer.close()


# ---------- consumer lag: the slow-consumer alert of Flow D ----------


@dataclass(frozen=True)
class TopicLag:
    """What a consumer group has not read yet on one topic (all partitions together)."""

    topic: str
    unread: int
    oldest_unread_at: datetime | None
    """When the oldest unread message was written; None if nothing is unread."""


def consumer_lag(
    bootstrap: str, group_id: str, topics: Sequence[str], *, timeout_s: float = 5.0
) -> list[TopicLag]:
    """Unread messages of ``group_id`` on ``topics`` (patterns starting with ``^`` are matched
    against the cluster's topics), and the write time of the oldest unread one: the slow
    consumer alert of section 8 of docs/01-business-spec.md.

    A partition with no committed offset counts from its first message, as the consumers do
    (``auto.offset.reset=earliest``). The group is only read, never joined or committed.
    """
    consumer = Consumer(
        {
            **consumer_config(bootstrap, group_id, f"{group_id}-lag"),
            "enable.partition.eof": False,
        }
    )
    try:
        names = sorted(consumer.list_topics(timeout=timeout_s).topics)
        wanted = sorted(
            {
                name
                for t in topics
                for name in names
                if (re.match(t, name) if t.startswith("^") else name == t)
            }
        )
        meta = consumer.list_topics(timeout=timeout_s).topics
        partitions = [
            TopicPartition(name, p) for name in wanted for p in sorted(meta[name].partitions)
        ]
        committed = consumer.committed(partitions, timeout=timeout_s) if partitions else []
        unread: dict[str, int] = dict.fromkeys(wanted, 0)
        starts: list[TopicPartition] = []
        for tp in committed:
            low, high = consumer.get_watermark_offsets(
                TopicPartition(tp.topic, tp.partition), timeout=timeout_s
            )
            start = tp.offset if tp.offset >= 0 else low
            if high > start:
                unread[tp.topic] += high - start
                starts.append(TopicPartition(tp.topic, tp.partition, start))
        oldest: dict[str, datetime] = {}
        if starts:
            consumer.assign(starts)
            pending = {(tp.topic, tp.partition) for tp in starts}
            deadline = time.monotonic() + timeout_s
            while pending and time.monotonic() < deadline:
                msg = consumer.poll(0.5)
                if msg is None or msg.error() is not None:
                    continue
                key = (msg.topic() or "", msg.partition() or 0)
                if key not in pending:
                    continue
                pending.discard(key)
                _kind, millis = msg.timestamp()
                at = datetime.fromtimestamp(millis / 1000, UTC)
                if key[0] not in oldest or at < oldest[key[0]]:
                    oldest[key[0]] = at
        return [TopicLag(t, unread[t], oldest.get(t)) for t in wanted]
    finally:
        consumer.close()
