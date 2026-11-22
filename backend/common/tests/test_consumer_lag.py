"""The slow-consumer alert of Flow D (section 8 of docs/01-business-spec.md) against the real
Kafka cluster (tier 3): ``consumer_lag`` and ``ConsumerMonitor`` behind ``GET /monitor`` of
Inventory and the Kitchen."""

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from common.clock import SystemClock
from common.kafka import Outgoing, Receiver, Sender, consumer_lag
from common.monitor import ConsumerMonitor

pytestmark = pytest.mark.tier3


def write(bootstrap: str, topic: str, keys: list[str]) -> None:
    sent = Sender(bootstrap, "test-lag").send_all(
        [Outgoing(topic, k.encode(), b"{}") for k in keys]
    )
    assert all(sent)


def test_unread_messages_and_the_oldest_one_per_topic(
    new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    topic, quiet = new_topic(2), new_topic(1)
    group = f"g-{uuid.uuid4().hex[:8]}"
    before = datetime.now(UTC) - timedelta(seconds=1)
    write(kafka_bootstrap, topic, ["a", "b", "c"])

    # Never committed: everything counts, from each partition's first message. A pattern
    # matches the cluster's topics as the services' subscriptions do.
    lags = {
        lag.topic: lag
        for lag in consumer_lag(kafka_bootstrap, group, [rf"^{topic.replace('.', r'\.')}$", quiet])
    }
    assert set(lags) == {topic, quiet}
    assert lags[topic].unread == 3
    oldest = lags[topic].oldest_unread_at
    assert oldest is not None and before <= oldest <= datetime.now(UTC)
    assert (lags[quiet].unread, lags[quiet].oldest_unread_at) == (0, None)

    # The group reads and commits one message: one fewer unread.
    receiver = Receiver(kafka_bootstrap, group, [topic], "test-lag-reader")
    try:
        deadline = time.monotonic() + 30
        record = None
        while record is None:
            assert time.monotonic() < deadline
            record = receiver.poll(0.5)
        receiver.commit(record)
    finally:
        receiver.close()
    [after] = consumer_lag(kafka_bootstrap, group, [topic])
    assert after.unread == 2


def test_a_topic_is_slow_when_its_oldest_unread_message_passes_the_threshold(
    new_topic: Callable[[int], str], kafka_bootstrap: str
) -> None:
    topic, quiet = new_topic(1), new_topic(1)
    write(kafka_bootstrap, topic, ["a"])
    time.sleep(1.1)
    monitor = ConsumerMonitor(
        kafka_bootstrap,
        f"g-{uuid.uuid4().hex[:8]}",
        [topic, quiet],
        SystemClock(),
        slow_after=timedelta(seconds=1),
    )
    view = monitor.view()
    assert view["kafka_reachable"] and view["slow_after_s"] == 1
    states = {t["topic"]: t for t in view["topics"]}
    assert states[topic]["slow"] and states[topic]["oldest_unread_age_s"] >= 1
    assert states[quiet] | {"topic": None} == {
        "topic": None,
        "unread": 0,
        "oldest_unread_at": None,
        "oldest_unread_age_s": None,
        "slow": False,
    }


def test_without_kafka_the_monitor_says_so() -> None:
    view = ConsumerMonitor(None, "g", ["x"], SystemClock()).view()
    assert (view["kafka_reachable"], view["topics"]) == (False, [])


@pytest.mark.parametrize(
    ("service", "expected"),
    [
        ("kitchen", {"kitchen-orders", "menu-events", "cancel-events.POS01"}),
        ("inventory", {"stock-commands", "order-events.POS01"}),
    ],
)
def test_the_services_monitor_their_own_topics(
    kafka_bootstrap: str, service: str, expected: set[str]
) -> None:
    """``GET /monitor`` of the running cluster's topics, for the service's consumer group."""
    if service == "kitchen":
        from kitchen_service.app import app
    else:
        from inventory_service.app import app
    body = TestClient(app).get("/monitor").json()
    assert body["consumer_group"] == service and body["kafka_reachable"]
    assert body["slow_after_s"] == 300
    assert expected <= {t["topic"] for t in body["topics"]}
