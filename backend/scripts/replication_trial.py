"""Trial run of logical replication to the Central Order Replica (risk 2, section 6 of
docs/03-implementation-plan.md).

Uses the pos01-db and central-db containers of infra/compose.yaml and the publication and
subscription at the end of section 5 of docs/02-detailed-design.md. It checks three things:

1. An order and a heartbeat written at the branch reach the central DB.
2. While replication from the branch is stopped (subscription disabled), the branch keeps
   beating but the central "data as of" value stops moving; it moves again once replication
   resumes. This is what scenario 55 shows.
3. While the central DB is unreachable (its container paused), orders written at the branch
   are kept and arrive after it comes back.

    ./bin/backend uv run python scripts/replication_trial.py

It leaves the publication, the subscription and the test rows in place; the branch rows carry
the branch id TRIAL so they are easy to tell apart.
"""
# pyright: basic
# The docker SDK has no type information; this script is infrastructure, not service code.

import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import docker
import psycopg

from common.migrate import apply_migrations

ROOT = Path(__file__).resolve().parents[1]
BRANCH_DSN = "host=pos01-db dbname=branch user=app password=app"
CENTRAL_DSN = "host=central-db dbname=central user=app password=app"
PROJECT = "order-system"


def wait_until(what: str, check: Callable[[], bool], timeout_s: float = 30) -> float:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if check():
            return time.monotonic() - start
        time.sleep(0.2)
    raise SystemExit(f"FAILED: {what} within {timeout_s:.0f}s")


def central_has_order(order_id: uuid.UUID) -> bool:
    with psycopg.connect(CENTRAL_DSN) as conn:
        return (
            conn.execute("SELECT 1 FROM orders WHERE order_id = %s", (order_id,)).fetchone()
            is not None
        )


def central_beat() -> datetime | None:
    with psycopg.connect(CENTRAL_DSN) as conn:
        row = conn.execute(
            "SELECT beat_at FROM replication_heartbeat WHERE branch_id = 'TRIAL'"
        ).fetchone()
    return row[0] if row else None


def beat(branch: psycopg.Connection) -> datetime:
    row = branch.execute(
        "INSERT INTO replication_heartbeat (branch_id, beat_at) VALUES ('TRIAL', now()) "
        "ON CONFLICT (branch_id) DO UPDATE SET beat_at = EXCLUDED.beat_at RETURNING beat_at"
    ).fetchone()
    assert row is not None
    return row[0]


def new_order(branch: psycopg.Connection) -> uuid.UUID:
    order_id = uuid.uuid4()
    branch.execute(
        "INSERT INTO orders (order_id, branch_id, status, items, created_at) "
        "VALUES (%s, 'TRIAL', 'CHO_KHO', '[]', now())",
        (order_id,),
    )
    return order_id


def container(service: str):
    found = docker.from_env().containers.list(
        filters={
            "label": [
                f"com.docker.compose.project={PROJECT}",
                f"com.docker.compose.service={service}",
            ]
        }
    )
    if not found:
        raise SystemExit(
            f"container of {service} is not running: docker compose -f infra/compose.yaml up -d"
        )
    return found[0]


def main() -> int:
    with psycopg.connect(BRANCH_DSN) as conn:
        apply_migrations(conn, ROOT / "order-service" / "migrations")
    with psycopg.connect(CENTRAL_DSN) as conn:
        apply_migrations(conn, ROOT / "query-service" / "migrations")

    with psycopg.connect(BRANCH_DSN, autocommit=True) as branch:
        if (
            branch.execute("SELECT 1 FROM pg_publication WHERE pubname = 'central_pub'").fetchone()
            is None
        ):
            branch.execute("CREATE PUBLICATION central_pub FOR TABLE orders, replication_heartbeat")
    with psycopg.connect(CENTRAL_DSN, autocommit=True) as central:
        if (
            central.execute("SELECT 1 FROM pg_subscription WHERE subname = 'sub_pos01'").fetchone()
            is None
        ):
            central.execute(
                "CREATE SUBSCRIPTION sub_pos01 CONNECTION "
                "'host=pos01-db dbname=branch user=app password=app' PUBLICATION central_pub"
            )
        central.execute("ALTER SUBSCRIPTION sub_pos01 ENABLE")

    with psycopg.connect(BRANCH_DSN, autocommit=True) as branch:
        # 1. Rows reach the central DB.
        order_id = new_order(branch)
        written = beat(branch)
        lag = wait_until("the order reaches central-db", lambda: central_has_order(order_id))
        wait_until("the heartbeat reaches central-db", lambda: central_beat() == written)
        print(f"1. order and heartbeat replicated, order after {lag:.2f}s")

        # 2. Replication stopped: the branch keeps beating, "data as of" stands still.
        with psycopg.connect(CENTRAL_DSN, autocommit=True) as central:
            central.execute("ALTER SUBSCRIPTION sub_pos01 DISABLE")
        frozen = central_beat()
        for _ in range(5):
            time.sleep(1)
            last_written = beat(branch)
        stood_still = central_beat() == frozen
        print(
            f"2. subscription disabled for 5s: central beat_at stood still = {stood_still} "
            f"(central {frozen:%H:%M:%S}, branch {last_written:%H:%M:%S})"
        )
        with psycopg.connect(CENTRAL_DSN, autocommit=True) as central:
            central.execute("ALTER SUBSCRIPTION sub_pos01 ENABLE")
        catch_up = wait_until("beat_at moves again", lambda: central_beat() == last_written)
        print(f"   re-enabled: central caught up after {catch_up:.2f}s")
        if not stood_still:
            return 1

        # 3. Central DB unreachable: rows written meanwhile arrive later.
        central_db = container("central-db")
        central_db.pause()
        try:
            during = [new_order(branch) for _ in range(3)]
            time.sleep(5)
        finally:
            central_db.unpause()
        late = wait_until(
            "orders written while central-db was paused arrive",
            lambda: all(central_has_order(o) for o in during),
            timeout_s=60,
        )
        print(
            "3. central-db paused for 5s: 3 orders written meanwhile arrived "
            f"{late:.2f}s after it came back"
        )

    print(f"Replication trial passed at {datetime.now(UTC):%Y-%m-%d %H:%M:%S} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
