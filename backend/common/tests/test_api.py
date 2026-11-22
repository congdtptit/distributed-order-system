"""The services' database dependency: a bounded connection pool per process.

Found by the performance test (step 7): with one new connection per request, 250 requests at
once exceeded PostgreSQL's 100 connections and the services answered 500. A request now waits
for a pooled connection; only a wait past the pool's timeout fails, with 503."""

import contextlib
import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import anyio.to_thread
import psycopg
import pytest
import uvicorn
from fastapi import Depends, FastAPI, HTTPException

from common import api


@pytest.fixture
def pooled(fresh_db: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("DATABASE_URL", fresh_db)
    monkeypatch.setenv("DB_POOL_SIZE", "2")
    yield fresh_db
    api.close_pools()


def use(hold_s: float, results: list[Any]) -> None:
    """One request: take a connection the way FastAPI runs the dependency, use it, give it back."""
    dependency = api.get_conn()
    try:
        conn = next(dependency)
        conn.execute("SELECT 1")
        time.sleep(hold_s)
        results.append("ok")
    except BaseException as exc:
        results.append(exc)
        return
    with contextlib.suppress(StopIteration):
        next(dependency)


def server_connections(dsn: str) -> int:
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ).fetchone()
    assert row is not None
    return int(row[0])


def test_more_requests_than_connections_wait_instead_of_failing(pooled: str) -> None:
    results: list[Any] = []
    peak = 0
    threads = [threading.Thread(target=use, args=(0.2, results)) for _ in range(10)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        peak = max(peak, server_connections(pooled))
        time.sleep(0.02)
    for t in threads:
        t.join()
    assert results == ["ok"] * 10
    assert 1 <= peak <= 2


def test_a_request_commits_its_work_and_the_connection_is_reused(pooled: str) -> None:
    dependency = api.get_conn()
    conn = next(dependency)
    conn.execute("CREATE TABLE t (x INT)")
    conn.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(StopIteration):
        next(dependency)
    with psycopg.connect(pooled) as other:
        assert other.execute("SELECT count(*) FROM t").fetchone() == (1,)


def test_a_request_that_fails_leaves_nothing_behind(pooled: str) -> None:
    with psycopg.connect(pooled) as setup:
        setup.execute("CREATE TABLE t (x INT)")
    dependency = api.get_conn()
    conn = next(dependency)
    conn.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(ValueError):
        dependency.throw(ValueError("the handler failed"))
    with psycopg.connect(pooled) as other:
        assert other.execute("SELECT count(*) FROM t").fetchone() == (0,)


def serve(app: FastAPI) -> tuple[uvicorn.Server, int]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = int(s.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the test server did not start"
        time.sleep(0.02)
    return server, port


def test_many_requests_through_a_real_server_do_not_starve_the_thread_pool(
    pooled: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second fault the performance test found: FastAPI runs the sync dependency in
    anyio's thread pool. When every thread of that pool waits for a pooled connection, the
    requests holding the connections get no thread to finish on, and everything stalls until
    the wait times out. Here the thread pool has 4 threads, the connection pool 2, and 20
    requests arrive at once: all must succeed well before the timeout."""
    monkeypatch.setattr(api, "POOL_WAIT_S", 5.0)

    @asynccontextmanager
    async def few_threads(_app: FastAPI) -> AsyncGenerator[None]:
        anyio.to_thread.current_default_thread_limiter().total_tokens = 4
        yield

    app = FastAPI(lifespan=few_threads)

    @app.get("/work")
    def work(conn: Annotated[psycopg.Connection[Any], Depends(api.get_conn)]) -> int:
        time.sleep(0.05)
        row = conn.execute("SELECT 1").fetchone()
        assert row is not None
        return int(row[0])

    server, port = serve(app)
    codes: list[int] = []

    def request() -> None:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/work", timeout=20) as r:
                codes.append(r.status)
        except urllib.error.HTTPError as exc:
            codes.append(exc.code)

    try:
        started = time.monotonic()
        threads = [threading.Thread(target=request) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        took = time.monotonic() - started
    finally:
        server.should_exit = True
    assert codes == [200] * 20
    assert took < 4, f"took {took:.1f} s: requests waited for the pool's timeout"


def test_a_wait_past_the_timeout_is_503(pooled: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "POOL_WAIT_S", 0.3)
    holders = [api.get_conn() for _ in range(2)]
    for h in holders:
        next(h)
    late = api.get_conn()
    with pytest.raises(HTTPException) as caught:
        next(late)
    assert caught.value.status_code == 503
    for h in holders:
        with pytest.raises(StopIteration):
            next(h)
