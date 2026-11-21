"""Apply numbered SQL migrations to one database.

Files are named ``NNN_description.sql`` and applied in number order, each in its own
transaction. The checksum of each applied file is recorded in ``schema_migrations``.
Applied migrations are immutable: a file whose content changed after it was applied, or
that disappeared, stops the run. A change goes into a new file with the next number.

    python -m common.migrate <dsn> <migrations directory>
"""

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from psycopg.rows import TupleRow

_FILE_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
_LOCK_KEY = 7_420_001  # any fixed number; only this runner takes this advisory lock

_CREATE_LEDGER = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  checksum   TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class MigrationError(Exception):
    """The migrations on disk and the ones recorded in the database disagree."""


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    checksum: str


def discover(directory: Path) -> list[Migration]:
    """Return the migration files of a directory, in version order."""
    found: list[Migration] = []
    for path in sorted(directory.iterdir()):
        if path.suffix != ".sql":
            continue
        match = _FILE_NAME.match(path.name)
        if match is None:
            raise MigrationError(f"{path.name}: migration files are named NNN_description.sql")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        found.append(Migration(match.group(1), path, checksum))
    versions = [m.version for m in found]
    duplicates = sorted({v for v in versions if versions.count(v) > 1})
    if duplicates:
        raise MigrationError(f"two migration files share the version {', '.join(duplicates)}")
    return found


def apply_migrations(conn: psycopg.Connection[TupleRow], directory: Path) -> list[str]:
    """Apply the migrations of ``directory`` that are not applied yet.

    Returns the file names applied by this call.
    """
    migrations = discover(directory)
    # Two instances of one service (Inventory runs two) start at the same time; the session
    # lock makes the second wait until the first has applied everything.
    conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
    try:
        return _apply(conn, directory, migrations)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))


def _apply(
    conn: psycopg.Connection[TupleRow], directory: Path, migrations: list[Migration]
) -> list[str]:
    with conn.transaction():
        conn.execute(_CREATE_LEDGER)
        rows = conn.execute("SELECT version, name, checksum FROM schema_migrations").fetchall()
    applied: dict[str, tuple[str, str]] = {str(v): (str(n), str(c)) for v, n, c in rows}

    on_disk = {m.version for m in migrations}
    missing = sorted(v for v in applied if v not in on_disk)
    if missing:
        names = ", ".join(applied[v][0] for v in missing)
        raise MigrationError(f"applied migrations are missing from {directory}: {names}")

    newly_applied: list[str] = []
    for migration in migrations:
        recorded = applied.get(migration.version)
        if recorded is not None:
            if recorded[1] != migration.checksum:
                raise MigrationError(
                    f"{migration.path.name} changed after it was applied; "
                    "put the change in a new migration file"
                )
            continue
        # The migration files are part of this repository, not user input.
        statement = cast(LiteralString, migration.path.read_text(encoding="utf-8"))
        with conn.transaction():
            conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                (migration.version, migration.path.name, migration.checksum),
            )
        newly_applied.append(migration.path.name)
    return newly_applied


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m common.migrate <dsn> <migrations directory>", file=sys.stderr)
        return 2
    dsn, directory = argv[1], Path(argv[2])
    with psycopg.connect(dsn) as conn:
        names = apply_migrations(conn, directory)
    print(f"applied {len(names)} migration(s)" + (": " + ", ".join(names) if names else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
