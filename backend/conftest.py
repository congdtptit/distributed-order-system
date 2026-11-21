"""Fixtures shared by every module's tests.

The tests run against the ``test-db`` PostgreSQL of compose.yaml (in CI, a PostgreSQL service
of the workflow), and each test gets a new, empty database in it. Tests never delete rows to
reset state: prohibition 1 in section 9 of docs/01-business-spec.md forbids deleting order
records, so a clean state means a new database.

``TEST_DATABASE_URL`` points at the server's default database.
"""

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from common.migrate import apply_migrations

ROOT = Path(__file__).parent
DEFAULT_TEST_DATABASE_URL = "postgresql://app:app@test-db:5432/postgres"


@pytest.fixture(scope="session")
def postgres_server() -> str:
    """Connection string of the test server's default database."""
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture
def fresh_db(postgres_server: str) -> str:
    """Connection string of a new, empty database."""
    name = f"t_{uuid.uuid4().hex[:16]}"
    with psycopg.connect(postgres_server, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    return make_conninfo(postgres_server, dbname=name)


def migrated_db(dsn: str, module: str) -> str:
    """Apply the migrations of one module (for example ``inventory-service``) to ``dsn``."""
    with psycopg.connect(dsn) as conn:
        apply_migrations(conn, ROOT / module / "migrations")
    return dsn
