"""The migration runner: order, idempotence, and immutability of applied files."""

from pathlib import Path

import psycopg
import pytest

from common.migrate import MigrationError, apply_migrations, discover


def _write(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def _tables(conn: psycopg.Connection[tuple[object, ...]]) -> set[str]:
    rows = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'").fetchall()
    return {str(r[0]) for r in rows}


def test_applies_files_in_number_order_once(fresh_db: str, tmp_path: Path) -> None:
    _write(tmp_path, "002_second.sql", "ALTER TABLE a ADD COLUMN y INT;")
    _write(tmp_path, "001_first.sql", "CREATE TABLE a (x INT);")
    with psycopg.connect(fresh_db) as conn:
        assert apply_migrations(conn, tmp_path) == ["001_first.sql", "002_second.sql"]
        assert apply_migrations(conn, tmp_path) == []
        _write(tmp_path, "003_third.sql", "CREATE TABLE b (x INT);")
        assert apply_migrations(conn, tmp_path) == ["003_third.sql"]
        assert _tables(conn) == {"a", "b", "schema_migrations"}


def test_refuses_an_applied_file_that_changed(fresh_db: str, tmp_path: Path) -> None:
    path = _write(tmp_path, "001_first.sql", "CREATE TABLE a (x INT);")
    with psycopg.connect(fresh_db) as conn:
        apply_migrations(conn, tmp_path)
        path.write_text("CREATE TABLE a (x BIGINT);", encoding="utf-8")
        with pytest.raises(MigrationError, match="changed after it was applied"):
            apply_migrations(conn, tmp_path)


def test_refuses_when_an_applied_file_is_missing(fresh_db: str, tmp_path: Path) -> None:
    path = _write(tmp_path, "001_first.sql", "CREATE TABLE a (x INT);")
    with psycopg.connect(fresh_db) as conn:
        apply_migrations(conn, tmp_path)
        path.unlink()
        with pytest.raises(MigrationError, match="missing"):
            apply_migrations(conn, tmp_path)


def test_a_failing_file_leaves_nothing_behind(fresh_db: str, tmp_path: Path) -> None:
    _write(tmp_path, "001_first.sql", "CREATE TABLE a (x INT);")
    _write(tmp_path, "002_broken.sql", "CREATE TABLE b (x INT); CREATE TABLE a (x INT);")
    with psycopg.connect(fresh_db) as conn:
        with pytest.raises(psycopg.errors.DuplicateTable):
            apply_migrations(conn, tmp_path)
        assert _tables(conn) == {"a", "schema_migrations"}
        recorded = conn.execute("SELECT name FROM schema_migrations").fetchall()
        assert [r[0] for r in recorded] == ["001_first.sql"]


@pytest.mark.parametrize("name", ["1_short.sql", "001-dash.sql", "001_Upper.sql"])
def test_refuses_badly_named_files(tmp_path: Path, name: str) -> None:
    _write(tmp_path, name, "SELECT 1;")
    with pytest.raises(MigrationError, match="NNN_description"):
        discover(tmp_path)
