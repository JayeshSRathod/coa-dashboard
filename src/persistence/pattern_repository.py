"""Append-only persistence for CQRP pattern-discovery candidates."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.pattern_discovery.models import PatternCandidate

from .repository import SQLiteRepository


def install_pattern_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS pattern_candidates (
            pattern_id TEXT PRIMARY KEY,
            experiment_id TEXT,
            source_run_id TEXT,
            statistics_snapshot_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            discovery_method TEXT NOT NULL,
            direction TEXT NOT NULL,
            definition_json TEXT NOT NULL,
            sample_size INTEGER NOT NULL,
            comparison_sample_size INTEGER NOT NULL,
            support_rate REAL NOT NULL,
            baseline_rate REAL,
            uplift REAL,
            average_r_multiple REAL,
            expectancy_r REAL,
            confidence_score REAL NOT NULL,
            stability_score REAL NOT NULL,
            evidence_ids_json TEXT NOT NULL,
            supporting_metrics_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            pattern_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_pattern_status_time
            ON pattern_candidates(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_pattern_experiment_time
            ON pattern_candidates(experiment_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_pattern_method_time
            ON pattern_candidates(discovery_method, created_at);

        CREATE TRIGGER IF NOT EXISTS pattern_candidates_no_update
            BEFORE UPDATE ON pattern_candidates BEGIN
            SELECT RAISE(ABORT, 'pattern_candidates is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS pattern_candidates_no_delete
            BEFORE DELETE ON pattern_candidates BEGIN
            SELECT RAISE(ABORT, 'pattern_candidates is append-only');
            END;
        """
    )


class PatternRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_pattern_schema(connection)

    def append(self, candidate: PatternCandidate) -> str:
        values = candidate.as_dict()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO pattern_candidates (
                    pattern_id, experiment_id, source_run_id, statistics_snapshot_id,
                    title, description, status, discovery_method, direction,
                    definition_json, sample_size, comparison_sample_size,
                    support_rate, baseline_rate, uplift, average_r_multiple,
                    expectancy_r, confidence_score, stability_score,
                    evidence_ids_json, supporting_metrics_json, warnings_json,
                    pattern_version, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["pattern_id"], values["experiment_id"], values["source_run_id"], values["statistics_snapshot_id"],
                    values["title"], values["description"], values["status"], values["discovery_method"], values["direction"],
                    json.dumps(values["definition"], sort_keys=True, default=str), values["sample_size"], values["comparison_sample_size"],
                    values["support_rate"], values["baseline_rate"], values["uplift"], values["average_r_multiple"],
                    values["expectancy_r"], values["confidence_score"], values["stability_score"],
                    json.dumps(values["evidence_ids"], sort_keys=True, default=str),
                    json.dumps(values["supporting_metrics"], sort_keys=True, default=str),
                    json.dumps(values["warnings"], sort_keys=True, default=str),
                    values["pattern_version"], values["created_at"], values["created_by"],
                ),
            )
        return candidate.pattern_id

    def get(self, pattern_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM pattern_candidates WHERE pattern_id=?", (pattern_id,)
        ).fetchone()
        return self._decode(row) if row else None

    def list(
        self,
        *,
        status: str | None = None,
        experiment_id: str | None = None,
        discovery_method: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM pattern_candidates WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status.upper())
        if experiment_id:
            query += " AND experiment_id=?"
            params.append(experiment_id)
        if discovery_method:
            query += " AND discovery_method=?"
            params.append(discovery_method.upper())
        query += " ORDER BY confidence_score DESC, stability_score DESC, created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return [self._decode(row) for row in self.connection.execute(query, params).fetchall()]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["definition"] = json.loads(item.pop("definition_json"))
        item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
        item["supporting_metrics"] = json.loads(item.pop("supporting_metrics_json"))
        item["warnings"] = json.loads(item.pop("warnings_json"))
        return item
