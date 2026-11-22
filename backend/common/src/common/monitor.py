"""``GET /monitor`` of Inventory and the Kitchen: the slow-consumer alert of Flow D.

Section 8 of docs/01-business-spec.md: an unread message older than the threshold of section
10 (5 minutes, proposed) raises an alert for its topic. The screens poll every 2 seconds, so a
reading is kept for a few seconds instead of asking Kafka on every request.
"""

import threading
import time
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from confluent_kafka import KafkaException

from common.clock import Clock
from common.kafka import TopicLag, consumer_lag

SLOW_AFTER = timedelta(minutes=5)
CACHE_S = 3.0


class ConsumerMonitor:
    def __init__(
        self,
        bootstrap: str | None,
        group_id: str,
        topics: Sequence[str],
        clock: Clock,
        *,
        slow_after: timedelta = SLOW_AFTER,
    ) -> None:
        self._bootstrap = bootstrap
        self._group = group_id
        self._topics = list(topics)
        self._clock = clock
        self._slow_after = slow_after
        self._lock = threading.Lock()
        self._cached: tuple[float, list[TopicLag] | None] | None = None

    def view(self) -> dict[str, Any]:
        lags = self._lags()
        now = self._clock.now()
        topics: list[dict[str, Any]] = []
        for lag in lags or []:
            age = None if lag.oldest_unread_at is None else (now - lag.oldest_unread_at)
            topics.append(
                {
                    "topic": lag.topic,
                    "unread": lag.unread,
                    "oldest_unread_at": lag.oldest_unread_at,
                    "oldest_unread_age_s": None
                    if age is None
                    else max(0, int(age.total_seconds())),
                    "slow": age is not None and age > self._slow_after,
                }
            )
        return {
            "consumer_group": self._group,
            "slow_after_s": int(self._slow_after.total_seconds()),
            "kafka_reachable": lags is not None,
            "topics": topics,
        }

    def _lags(self) -> list[TopicLag] | None:
        """None when Kafka cannot be asked."""
        with self._lock:
            if self._cached and time.monotonic() - self._cached[0] < CACHE_S:
                return self._cached[1]
            lags: list[TopicLag] | None
            if self._bootstrap is None:
                lags = None
            else:
                try:
                    lags = consumer_lag(self._bootstrap, self._group, self._topics)
                except KafkaException:
                    lags = None
            self._cached = (time.monotonic(), lags)
            return lags
