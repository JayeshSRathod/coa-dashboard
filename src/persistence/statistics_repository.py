"""Append-only persistence for CQRP statistics snapshots."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.statistics.models import StatisticsSnapshot

from .repository import SQLiteRepository


def install_statistics_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS statistics_snapshots (
            statistics_id TEXT PRIMARY KEY,
            scope_type TEXT NOT NULL,
            scope_value TEXT NOT NULL,
            evidence_count INTEGER NOT NULL,
            report_json TEXT NOT NULL,
            statistics_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_statistics_scope_time
            ON statistics_snapshots(scope_type, scope_value, created_at);

        CREATE TRIGGER IF NOT EXISTS statistics_snapshots_no_update
            BEFORE UPDATE ON statistics_snapshots BEGIN
            SELECT RAISE(ABORT, 'statistics_snapshots is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS statistics_snapshots_no_delete
            BEFORE DELETE ON statistics_snapshots BEGIN
            SELECT RAISE(ABORT, 'statistics_snapshots is append-only');
            END;
        """
    )


class StatisticsRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_statistics_schema(connection)

    def append(self, snapshot: StatisticsSnapshot) -> str:
        values = snapshot.as_dict()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO statistics_snapshots (
                    statistics_id, scope_type, scope_value, evidence_count,
                    report_json, statistics_version, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["statistics_id"], values["scope_type"], values["scope_value"],
                    values["evidence_count"], json.dumps(values["report"], sort_keys=True, default=str),
                    values["statistics_version"], values["created_at"], values["created_by"],
                ),
            )
        return snapshot.statistics_id

    def get(self, statistics_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM statistics_snapshots WHERE statistics_id=?",
            (statistics_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def latest(self, scope_type: str, scope_value: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM statistics_snapshots WHERE scope_type=? AND scope_value=? "
            "ORDER BY created_at DESC, statistics_id DESC LIMIT 1",
            (scope_type.upper(), scope_value),
        ).fetchone()
        return self._decode(row) if row else None

    def history(self, scope_type: str, scope_value: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM statistics_snapshots WHERE scope_type=? AND scope_value=? "
            "ORDER BY created_at DESC, statistics_id DESC LIMIT ?",
            (scope_type.upper(), scope_value, max(1, min(int(limit), 1000))),
        ).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["report"] = json.loads(item.pop("report_json"))
        return item
