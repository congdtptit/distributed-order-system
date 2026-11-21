"""FastAPI dependencies shared by the services' HTTP APIs. Tests override them with
``app.dependency_overrides`` to use the test DB and a fixed clock."""

import os
from collections.abc import Iterator
from typing import Any

import psycopg

from common.clock import Clock, SystemClock


def get_conn() -> Iterator[psycopg.Connection[Any]]:
    """One transaction per request. Handlers that change data call ``conn.commit()`` before
    they return, so a 2xx answer means the change is stored; an error rolls back."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        yield conn


def get_clock() -> Clock:
    return SystemClock()
