"""Fixtures of the Order Query Service tests: a migrated Central Order Replica (the tests write
the replicated rows themselves) and the HTTP API on it."""

from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from common.api import get_conn
from query_service.app import app, get_branches

BRANCHES = ["POS01", "POS02", "ONLINE"]


@pytest.fixture
def cdb(migrated: Callable[[str], str]) -> str:
    return migrated("query-service")


@pytest.fixture
def api(cdb: str) -> Iterator[TestClient]:
    def conn() -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(cdb) as c:
            yield c

    app.dependency_overrides[get_conn] = conn
    app.dependency_overrides[get_branches] = lambda: BRANCHES
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
