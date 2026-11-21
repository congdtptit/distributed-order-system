"""Create the Kafka topics and check their settings.

Topics are those of section 13.1 of docs/01-business-spec.md, with the settings it makes
mandatory (3 replicas, min.insync.replicas=2, 7 days retention) and the partition counts of
point 6 in section 8 of docs/02-detailed-design.md. Topics are never auto-created
(section 2 of docs/03-implementation-plan.md).

The script can run any number of times: a topic that exists is checked, not recreated. It
exits 1 if an existing topic has different settings; such a topic must be fixed by hand.

    ./bin/backend uv run python scripts/create_topics.py

Environment: KAFKA_BOOTSTRAP (set in the backend-dev container),
BRANCHES (default POS01,POS02,ONLINE).
"""
# pyright: basic, reportPrivateImportUsage=false
# confluent-kafka's admin API is only partly typed, and its documented imports from
# confluent_kafka.admin look private to pyright. This script is infrastructure, not service code.

import os
import sys
import time

from confluent_kafka.admin import (
    AdminClient,
    ConfigResource,
    NewTopic,
    ResourceType,
)

REPLICATION_FACTOR = 3
TOPIC_CONFIG = {
    "min.insync.replicas": "2",
    "retention.ms": str(7 * 24 * 60 * 60 * 1000),
}


def wanted_topics(branches: list[str]) -> dict[str, int]:
    """Topic name -> partition count."""
    topics: dict[str, int] = {}
    for branch in branches:
        topics[f"order-events.{branch}"] = 2
        topics[f"cancel-events.{branch}"] = 2
        topics[f"status-events.{branch}"] = 1
    topics.update({"kitchen-orders": 2, "stock-commands": 2, "menu-events": 1, "dlq": 1})
    return topics


def wait_for_brokers(admin: AdminClient, expected: int, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            brokers = admin.list_topics(timeout=5).brokers
            if len(brokers) >= expected:
                return
        except Exception as exc:  # the cluster may still be starting
            brokers = {}
            last_error = exc
        else:
            last_error = None
        if time.monotonic() > deadline:
            raise SystemExit(
                f"only {len(brokers)} of {expected} brokers answered after {timeout_s:.0f}s"
                + (f": {last_error}" if last_error else "")
            )
        time.sleep(2)


def main() -> int:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092,localhost:9094,localhost:9096")
    branches = os.environ.get("BRANCHES", "POS01,POS02,ONLINE").split(",")
    wanted = wanted_topics([b.strip() for b in branches if b.strip()])

    admin = AdminClient({"bootstrap.servers": bootstrap})
    wait_for_brokers(admin, REPLICATION_FACTOR, timeout_s=120)

    existing = admin.list_topics(timeout=10).topics
    to_create = [
        NewTopic(
            name, num_partitions=parts, replication_factor=REPLICATION_FACTOR, config=TOPIC_CONFIG
        )
        for name, parts in wanted.items()
        if name not in existing
    ]
    if to_create:
        for name, future in admin.create_topics(to_create, operation_timeout=30).items():
            future.result()
            print(f"created {name}")

    problems: list[str] = []
    topics = admin.list_topics(timeout=10).topics
    resources = [ConfigResource(ResourceType.TOPIC, name) for name in wanted]
    configs = {res.name: fut.result() for res, fut in admin.describe_configs(resources).items()}
    for name, parts in wanted.items():
        meta = topics.get(name)
        if meta is None:
            problems.append(f"{name}: missing")
            continue
        if len(meta.partitions) != parts:
            problems.append(f"{name}: {len(meta.partitions)} partitions, expected {parts}")
        for pid, part in meta.partitions.items():
            if len(part.replicas) != REPLICATION_FACTOR:
                problems.append(f"{name}[{pid}]: {len(part.replicas)} replicas")
        for key, value in TOPIC_CONFIG.items():
            actual = configs[name][key].value
            if actual != value:
                problems.append(f"{name}: {key}={actual}, expected {value}")

    if problems:
        print("Topics that do not match 01 section 13.1 / 02 section 8 point 6:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"{len(wanted)} topics ok: replication {REPLICATION_FACTOR}, "
        f"min.insync.replicas {TOPIC_CONFIG['min.insync.replicas']}, retention 7 days "
        f"({len(to_create)} created now)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
