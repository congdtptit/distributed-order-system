"""Fixtures of the branch tests: a migrated branch DB with the dish catalogue, and the HTTP API
on that DB with a fixed clock, as branch POS01."""

from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from branch_support import BRANCH, NOW, with_dishes
from fastapi.testclient import TestClient

from common.api import get_clock, get_conn
from common.clock import FixedClock
from order_service.app import app, get_branch


@pytest.fixture
def bdb(migrated: Callable[[str], str]) -> str:
    return with_dishes(migrated("order-service"))


@pytest.fixture
def api(bdb: str) -> Iterator[TestClient]:
    def conn() -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(bdb) as c:
            yield c

    app.dependency_overrides[get_conn] = conn
    app.dependency_overrides[get_clock] = lambda: FixedClock(NOW)
    app.dependency_overrides[get_branch] = lambda: BRANCH
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
