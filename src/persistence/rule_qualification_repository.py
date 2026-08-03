"""Append-only persistence for CQRP shadow rule qualifications."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.rule_qualification.models import RuleQualificationResult

from .repository import SQLiteRepository


def install_rule_qualification_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS rule_qualifications (
            qualification_id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            pattern_id TEXT NOT NULL,
            validation_id TEXT NOT NULL,
            experiment_id TEXT,
            status TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            qualification_score REAL NOT NULL,
            definition_json TEXT NOT NULL,
            validation_score REAL NOT NULL,
            confidence_score REAL NOT NULL,
            stability_score REAL NOT NULL,
            evidence_score REAL NOT NULL,
            governance_score REAL NOT NULL,
            sample_size INTEGER NOT NULL,
            validation_sample_size INTEGER NOT NULL,
            required_conditions_json TEXT NOT NULL,
            failed_gates_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            lineage_json TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_qualifications_rule_version
            ON rule_qualifications(rule_id, rule_version);
        CREATE INDEX IF NOT EXISTS idx_rule_qualifications_status_score
            ON rule_qualifications(status, qualification_score DESC);
        CREATE INDEX IF NOT EXISTS idx_rule_qualifications_pattern_time
            ON rule_qualifications(pattern_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_rule_qualifications_validation
            ON rule_qualifications(validation_id);

        CREATE TRIGGER IF NOT EXISTS rule_qualifications_no_update
            BEFORE UPDATE ON rule_qualifications BEGIN
            SELECT RAISE(ABORT, 'rule_qualifications is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS rule_qualifications_no_delete
            BEFORE DELETE ON rule_qualifications BEGIN
            SELECT RAISE(ABORT, 'rule_qualifications is append-only');
            END;
        """
    )


class RuleQualificationRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_rule_qualification_schema(connection)

    def append(self, result: RuleQualificationResult) -> str:
        values = result.as_dict()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO rule_qualifications VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    values["qualification_id"], values["rule_id"], values["pattern_id"], values["validation_id"],
                    values["experiment_id"], values["status"], values["recommendation"], values["qualification_score"],
                    json.dumps(values["definition"], sort_keys=True, default=str), values["validation_score"],
                    values["confidence_score"], values["stability_score"], values["evidence_score"],
                    values["governance_score"], values["sample_size"], values["validation_sample_size"],
                    json.dumps(values["required_conditions"], sort_keys=True),
                    json.dumps(values["failed_gates"], sort_keys=True),
                    json.dumps(values["warnings"], sort_keys=True),
                    json.dumps(values["lineage"], sort_keys=True, default=str),
                    values["rule_version"], values["created_at"], values["created_by"],
                ),
            )
        return result.qualification_id

    def get(self, qualification_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM rule_qualifications WHERE qualification_id=?", (qualification_id,)
        ).fetchone()
        return self._decode(row) if row else None

    def latest_for_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM rule_qualifications WHERE pattern_id=? ORDER BY created_at DESC, qualification_id DESC LIMIT 1",
            (pattern_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def list(self, *, status: str | None = None, recommendation: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM rule_qualifications WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status.upper())
        if recommendation:
            query += " AND recommendation=?"
            params.append(recommendation.upper())
        query += " ORDER BY qualification_score DESC, created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return [self._decode(row) for row in self.connection.execute(query, params).fetchall()]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for field in ("definition_json", "required_conditions_json", "failed_gates_json", "warnings_json", "lineage_json"):
            item[field.removesuffix("_json")] = json.loads(item.pop(field))
        item["mode"] = "SHADOW_RULE_ONLY"
        return item
