"""The migrations of this service create exactly the tables of docs/02-detailed-design.md section
4.
"""

from pathlib import Path

import psycopg

from common.migrate import apply_migrations

MIGRATIONS = Path(__file__).parents[1] / "migrations"

TABLES = {
    "kitchen_orders",
    "flagged_ingredients",
    "alerts",
    "processed_events",
    "outbox_events",
}


def test_migrations_create_the_tables_of_the_design(fresh_db: str) -> None:
    with psycopg.connect(fresh_db) as conn:
        assert apply_migrations(conn, MIGRATIONS) == ["001_schema.sql"]
        assert apply_migrations(conn, MIGRATIONS) == []
        rows = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    assert {str(r[0]) for r in rows} - {"schema_migrations"} == TABLES
