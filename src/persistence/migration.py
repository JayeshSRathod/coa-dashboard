"""Migration registry boundary; concrete research migrations begin in Sprint-002."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

Migration = Callable[[sqlite3.Connection], None]


def apply_migrations(connection: sqlite3.Connection, migrations: list[Migration]) -> None:
    """Apply supplied migrations atomically; no schema is introduced in Sprint-001."""
    with connection:
        for migration in migrations:
            migration(connection)
