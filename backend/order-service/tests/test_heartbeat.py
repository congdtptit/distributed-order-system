"""The branch's replication heartbeat: one ``replication_heartbeat`` row per branch, moved
forward every few seconds, which gives the Management report its "data as of" time once it has
replicated to the Central Order Replica (section 5 of docs/02-detailed-design.md, "Replication
to the Central Order Replica"; scenario 55)."""

import threading
import time
from datetime import datetime
from typing import Any

import psycopg
import pytest
from branch_support import BRANCH

from order_service.heartbeat import Heartbeat, beat


def rows(dsn: str) -> list[tuple[str, datetime]]:
    with psycopg.connect(dsn) as conn:
        return [
            (str(r[0]), r[1])
            for r in conn.execute("SELECT branch_id, beat_at FROM replication_heartbeat")
        ]


def test_the_upsert_keeps_one_row_per_branch_and_moves_it_forward(bdb: str) -> None:
    with psycopg.connect(bdb) as conn:
        beat(conn, BRANCH)
        conn.commit()
    [(branch, first)] = rows(bdb)
    assert branch == BRANCH
    time.sleep(0.01)
    with psycopg.connect(bdb) as conn:
        beat(conn, BRANCH)
        conn.commit()
    [(branch, second)] = rows(bdb)
    assert branch == BRANCH
    assert second > first


def test_the_worker_beats_until_stopped(bdb: str) -> None:
    stop = threading.Event()
    worker = threading.Thread(
        target=Heartbeat(lambda: psycopg.connect(bdb), BRANCH, every_s=0.05).run, args=(stop,)
    )
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while not rows(bdb):
            assert time.monotonic() < deadline, "no heartbeat written"
            time.sleep(0.02)
        [(_, first)] = rows(bdb)
        while rows(bdb)[0][1] == first:
            assert time.monotonic() < deadline, "the heartbeat did not move"
            time.sleep(0.02)
    finally:
        stop.set()
        worker.join(5)
    assert not worker.is_alive()


def test_the_worker_survives_a_database_that_is_down(bdb: str) -> None:
    """The branch DB may restart; the beat resumes instead of the thread dying."""
    calls = {"n": 0}

    def connect() -> psycopg.Connection[Any]:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise psycopg.OperationalError("connection refused")
        return psycopg.connect(bdb)

    stop = threading.Event()
    worker = threading.Thread(target=Heartbeat(connect, BRANCH, every_s=0.05).run, args=(stop,))
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while not rows(bdb):
            assert time.monotonic() < deadline, "no heartbeat after the DB came back"
            time.sleep(0.02)
    finally:
        stop.set()
        worker.join(5)
    assert calls["n"] >= 3


@pytest.mark.parametrize("every_s", [0, -1])
def test_the_interval_must_be_positive(every_s: float) -> None:
    with pytest.raises(ValueError):
        Heartbeat(lambda: psycopg.connect(""), BRANCH, every_s=every_s)
