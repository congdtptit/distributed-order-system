"""FastAPI dependencies shared by the services' HTTP APIs. Tests override them with
``app.dependency_overrides`` to use the test DB and a fixed clock.

Requests take their connection from one bounded pool per process (``DB_POOL_SIZE``, default
10). The performance test of step 7 found that one new connection per request breaks under
load: 250 requests at once exceeded PostgreSQL's 100 connections and the services answered
500. With the pool a request waits for a connection; one that waits longer than
``POOL_WAIT_S`` gets 503. The background workers keep their own connections.

The wait happens in ``db_slot``, an async dependency, before ``get_conn`` runs. FastAPI runs
a sync dependency in anyio's thread pool (40 threads): had requests waited for the pool there,
the waiting requests would hold every thread, the requests holding the connections would get
none to finish on, and all would stall until the timeout (found by the same test). An async
wait holds no thread, and at most ``DB_POOL_SIZE`` requests reach the thread pool for a
connection, which is then always free.
"""

import os
import threading
from collections.abc import AsyncGenerator, Generator
from contextlib import ExitStack
from typing import Annotated, Any

import anyio
import psycopg
from fastapi import Depends, HTTPException
from psycopg_pool import ConnectionPool, PoolTimeout

from common.clock import Clock, SystemClock

POOL_WAIT_S = 30.0

_pools: dict[str, ConnectionPool[psycopg.Connection[Any]]] = {}
_pools_lock = threading.Lock()
_slots: anyio.Semaphore | None = None


def pool_size() -> int:
    return int(os.environ.get("DB_POOL_SIZE", "10"))


def _pool(dsn: str) -> ConnectionPool[psycopg.Connection[Any]]:
    with _pools_lock:
        pool = _pools.get(dsn)
        if pool is None:
            pool = ConnectionPool[psycopg.Connection[Any]](
                dsn,
                connection_class=psycopg.Connection,
                min_size=1,
                max_size=pool_size(),
                # A database that restarted leaves dead connections in the pool: check each
                # one before handing it out.
                check=ConnectionPool.check_connection,
                name="api",
                open=True,
            )
            _pools[dsn] = pool
        return pool


def close_pools() -> None:
    global _slots
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
        _slots = None


async def db_slot() -> AsyncGenerator[None]:
    """Wait, without holding a thread, until fewer than ``DB_POOL_SIZE`` requests of this
    process use the database."""
    global _slots
    if _slots is None:
        _slots = anyio.Semaphore(pool_size())
    slots = _slots
    try:
        with anyio.fail_after(POOL_WAIT_S):
            await slots.acquire()
    except TimeoutError as exc:
        raise HTTPException(503, "The database is busy; try again") from exc
    try:
        yield
    finally:
        slots.release()


def get_conn(
    _slot: Annotated[None, Depends(db_slot)] = None,
) -> Generator[psycopg.Connection[Any], None, None]:
    """One transaction per request. Handlers that change data call ``conn.commit()`` before
    they return, so a 2xx answer means the change is stored; an error rolls back. The
    connection goes back to the pool either way."""
    pool = _pool(os.environ["DATABASE_URL"])
    with ExitStack() as stack:
        try:
            conn = stack.enter_context(pool.connection(timeout=POOL_WAIT_S))
        except PoolTimeout as exc:
            raise HTTPException(503, "The database is busy; try again") from exc
        yield conn


def get_clock() -> Clock:
    return SystemClock()
