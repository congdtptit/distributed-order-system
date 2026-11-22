"""The migrations of this service create exactly the tables of
docs/02-detailed-design.md section 5.
"""

from pathlib import Path

import psycopg

from common.migrate import apply_migrations

MIGRATIONS = Path(__file__).parents[1] / "migrations"

TABLES = {
    "orders",
    "outbox_events",
    "menu_cache",
    "menu_cache_meta",
    "replication_heartbeat",
    "processed_events",
    "dishes",
    "alerts",
}


def test_migrations_create_the_tables_of_the_design(fresh_db: str) -> None:
    with psycopg.connect(fresh_db) as conn:
        assert apply_migrations(conn, MIGRATIONS) == [
            "001_schema.sql",
            "002_dishes.sql",
            "003_alerts.sql",
            "004_menu_sync.sql",
        ]
        assert apply_migrations(conn, MIGRATIONS) == []
        rows = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
        # 004 (Flow C): the one meta row, at epoch 0 before the first snapshot.
        meta = conn.execute(
            "SELECT epoch, newest_epoch, last_heard_at FROM menu_cache_meta"
        ).fetchall()
    assert meta == [(0, 0, None)]
    assert {str(r[0]) for r in rows} - {"schema_migrations"} == TABLES
