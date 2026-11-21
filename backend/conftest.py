"""Fixtures shared by every module's tests.

One PostgreSQL container serves the whole test session, and each test gets a new, empty
database in it. Tests never delete rows to reset state: prohibition 1 in section 9 of
docs/01-business-spec.md forbids deleting order records, so a clean state means a new database.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from testcontainers.community.postgres import PostgresContainer

from common.migrate import apply_migrations

POSTGRES_IMAGE = "postgres:16.14"
ROOT = Path(__file__).parent


@pytest.fixture(scope="session")
def postgres_server() -> Iterator[str]:
    """Connection string of the session's PostgreSQL server (its default database)."""
    with PostgresContainer(POSTGRES_IMAGE, driver=None) as container:
        yield container.get_connection_url()


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
