"""Versioned, transactional SQLite migration support."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3


MigrationFunction = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: MigrationFunction


def apply_migrations(connection: sqlite3.Connection, migrations: tuple[Migration, ...]) -> None:
    """Apply each unapplied migration once, in ascending version order."""
    with connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        applied = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for migration in sorted(migrations, key=lambda item: item.version):
            if migration.version in applied:
                continue
            migration.apply(connection)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?)",
                (migration.version, migration.name, datetime.now(timezone.utc).isoformat()),
            )
