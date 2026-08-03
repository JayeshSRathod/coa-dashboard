"""Append-only persistence for immutable CQRP evidence records."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.evidence.models import EvidenceRecord

from .repository import SQLiteRepository


def install_evidence_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            trade_plan_id TEXT,
            validation_id TEXT,
            execution_audit_id TEXT,
            signal_id TEXT,
            snapshot_id TEXT,
            experiment_id TEXT,
            instrument TEXT NOT NULL,
            planning_horizon TEXT NOT NULL,
            scenario_number INTEGER,
            scenario TEXT,
            direction TEXT NOT NULL,
            outcome TEXT NOT NULL,
            realized_pnl REAL NOT NULL,
            realized_r_multiple REAL,
            mfe REAL NOT NULL,
            mae REAL NOT NULL,
            holding_seconds REAL,
            confidence_score REAL,
            selected_plan TEXT,
            entry_price REAL,
            average_exit_price REAL,
            exit_reason TEXT,
            regime TEXT,
            feature_vector_json TEXT NOT NULL,
            lineage_json TEXT NOT NULL,
            evidence_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(trade_id, evidence_version)
        );

        CREATE INDEX IF NOT EXISTS idx_evidence_instrument_time
            ON evidence_records(instrument, created_at);
        CREATE INDEX IF NOT EXISTS idx_evidence_outcome_time
            ON evidence_records(outcome, created_at);
        CREATE INDEX IF NOT EXISTS idx_evidence_scenario_time
            ON evidence_records(scenario_number, created_at);
        CREATE INDEX IF NOT EXISTS idx_evidence_experiment_time
            ON evidence_records(experiment_id, created_at);

        CREATE TRIGGER IF NOT EXISTS evidence_records_no_update
            BEFORE UPDATE ON evidence_records BEGIN
            SELECT RAISE(ABORT, 'evidence_records is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS evidence_records_no_delete
            BEFORE DELETE ON evidence_records BEGIN
            SELECT RAISE(ABORT, 'evidence_records is append-only');
            END;
        """
    )


class EvidenceRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_evidence_schema(connection)

    def append(self, record: EvidenceRecord) -> str:
        values = record.as_dict()
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO evidence_records (
                        evidence_id, trade_id, trade_plan_id, validation_id,
                        execution_audit_id, signal_id, snapshot_id, experiment_id,
                        instrument, planning_horizon, scenario_number, scenario,
                        direction, outcome, realized_pnl, realized_r_multiple,
                        mfe, mae, holding_seconds, confidence_score, selected_plan,
                        entry_price, average_exit_price, exit_reason, regime,
                        feature_vector_json, lineage_json, evidence_version,
                        created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        values["evidence_id"], values["trade_id"], values["trade_plan_id"],
                        values["validation_id"], values["execution_audit_id"], values["signal_id"],
                        values["snapshot_id"], values["experiment_id"], values["instrument"],
                        values["planning_horizon"], values["scenario_number"], values["scenario"],
                        values["direction"], values["outcome"], values["realized_pnl"],
                        values["realized_r_multiple"], values["mfe"], values["mae"],
                        values["holding_seconds"], values["confidence_score"], values["selected_plan"],
                        values["entry_price"], values["average_exit_price"], values["exit_reason"],
                        values["regime"], json.dumps(values["feature_vector"], sort_keys=True, default=str),
                        json.dumps(values["lineage"], sort_keys=True, default=str), values["evidence_version"],
                        values["created_at"], values["created_by"],
                    ),
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_trade(record.trade_id, record.evidence_version)
            if existing is not None:
                return str(existing["evidence_id"])
            raise
        return record.evidence_id

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM evidence_records WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def get_for_trade(self, trade_id: str, evidence_version: str = "evidence-v1") -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM evidence_records WHERE trade_id=? AND evidence_version=?",
            (trade_id, evidence_version),
        ).fetchone()
        return self._decode(row) if row else None

    def list(
        self,
        *,
        instrument: str | None = None,
        outcome: str | None = None,
        scenario_number: int | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence_records WHERE 1=1"
        params: list[Any] = []
        if instrument:
            query += " AND instrument=?"
            params.append(instrument)
        if outcome:
            query += " AND outcome=?"
            params.append(outcome)
        if scenario_number is not None:
            query += " AND scenario_number=?"
            params.append(int(scenario_number))
        if experiment_id:
            query += " AND experiment_id=?"
            params.append(experiment_id)
        query += " ORDER BY created_at DESC, evidence_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return [self._decode(row) for row in self.connection.execute(query, params).fetchall()]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["feature_vector"] = json.loads(item.pop("feature_vector_json"))
        item["lineage"] = json.loads(item.pop("lineage_json"))
        return item
