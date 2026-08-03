"""Append-only persistence for CQRP experiment validation results."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.experiment_validation.models import ValidationResult

from .repository import SQLiteRepository


def install_experiment_validation_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS experiment_validations (
            validation_id TEXT PRIMARY KEY,
            pattern_id TEXT NOT NULL,
            experiment_id TEXT,
            status TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            validation_score REAL NOT NULL,
            discovery_sample_size INTEGER NOT NULL,
            validation_sample_size INTEGER NOT NULL,
            in_sample_win_rate REAL,
            out_of_sample_win_rate REAL,
            in_sample_expectancy_r REAL,
            out_of_sample_expectancy_r REAL,
            degradation_percent REAL,
            stability_score REAL NOT NULL,
            walk_forward_score REAL NOT NULL,
            bootstrap_score REAL NOT NULL,
            monte_carlo_score REAL NOT NULL,
            drift_score REAL NOT NULL,
            sensitivity_score REAL NOT NULL,
            metrics_json TEXT NOT NULL,
            evidence_ids_json TEXT NOT NULL,
            discovery_evidence_ids_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            lineage_json TEXT NOT NULL,
            validation_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_validations_pattern_time
            ON experiment_validations(pattern_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_experiment_validations_status_score
            ON experiment_validations(status, validation_score DESC);
        CREATE INDEX IF NOT EXISTS idx_experiment_validations_experiment_time
            ON experiment_validations(experiment_id, created_at);

        CREATE TRIGGER IF NOT EXISTS experiment_validations_no_update
            BEFORE UPDATE ON experiment_validations BEGIN
            SELECT RAISE(ABORT, 'experiment_validations is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS experiment_validations_no_delete
            BEFORE DELETE ON experiment_validations BEGIN
            SELECT RAISE(ABORT, 'experiment_validations is append-only');
            END;
        """
    )


class ExperimentValidationRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_experiment_validation_schema(connection)

    def append(self, result: ValidationResult) -> str:
        values = result.as_dict()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO experiment_validations VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    values["validation_id"], values["pattern_id"], values["experiment_id"], values["status"],
                    values["recommendation"], values["validation_score"], values["discovery_sample_size"],
                    values["validation_sample_size"], values["in_sample_win_rate"], values["out_of_sample_win_rate"],
                    values["in_sample_expectancy_r"], values["out_of_sample_expectancy_r"], values["degradation_percent"],
                    values["stability_score"], values["walk_forward_score"], values["bootstrap_score"],
                    values["monte_carlo_score"], values["drift_score"], values["sensitivity_score"],
                    json.dumps(values["metrics"], sort_keys=True, default=str),
                    json.dumps(values["evidence_ids"], sort_keys=True, default=str),
                    json.dumps(values["discovery_evidence_ids"], sort_keys=True, default=str),
                    json.dumps(values["warnings"], sort_keys=True, default=str),
                    json.dumps(values["lineage"], sort_keys=True, default=str),
                    values["validation_version"], values["created_at"], values["created_by"],
                ),
            )
        return result.validation_id

    def get(self, validation_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM experiment_validations WHERE validation_id=?", (validation_id,)
        ).fetchone()
        return self._decode(row) if row else None

    def latest_for_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM experiment_validations WHERE pattern_id=? ORDER BY created_at DESC, validation_id DESC LIMIT 1",
            (pattern_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def list(self, *, status: str | None = None, pattern_id: str | None = None, experiment_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM experiment_validations WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status.upper())
        if pattern_id:
            query += " AND pattern_id=?"
            params.append(pattern_id)
        if experiment_id:
            query += " AND experiment_id=?"
            params.append(experiment_id)
        query += " ORDER BY created_at DESC, validation_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return [self._decode(row) for row in self.connection.execute(query, params).fetchall()]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json"))
        item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
        item["discovery_evidence_ids"] = json.loads(item.pop("discovery_evidence_ids_json"))
        item["warnings"] = json.loads(item.pop("warnings_json"))
        item["lineage"] = json.loads(item.pop("lineage_json"))
        return item
