"""Append-only persistence for CQRP shadow-execution governance records."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.execution.audit import ExecutionAuditRecord

from .repository import SQLiteRepository


def install_execution_audit_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS execution_audits (
            audit_id TEXT PRIMARY KEY,
            trade_plan_id TEXT NOT NULL,
            validation_id TEXT,
            signal_id TEXT,
            snapshot_id TEXT,
            instrument TEXT NOT NULL,
            planning_horizon TEXT NOT NULL,
            policy_allowed INTEGER NOT NULL,
            execution_eligible INTEGER NOT NULL,
            action TEXT NOT NULL,
            paper_trade_id TEXT,
            reasons_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_execution_audits_plan_time
            ON execution_audits(trade_plan_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_execution_audits_action_time
            ON execution_audits(action, created_at);
        CREATE INDEX IF NOT EXISTS idx_execution_audits_instrument_time
            ON execution_audits(instrument, created_at);

        CREATE TRIGGER IF NOT EXISTS execution_audits_no_update
            BEFORE UPDATE ON execution_audits BEGIN
            SELECT RAISE(ABORT, 'execution_audits is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS execution_audits_no_delete
            BEFORE DELETE ON execution_audits BEGIN
            SELECT RAISE(ABORT, 'execution_audits is append-only');
            END;
        """
    )


class ExecutionAuditRepository(SQLiteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_execution_audit_schema(connection)

    def append(self, record: ExecutionAuditRecord) -> str:
        values = record.as_dict()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_audits (
                    audit_id, trade_plan_id, validation_id, signal_id,
                    snapshot_id, instrument, planning_horizon, policy_allowed,
                    execution_eligible, action, paper_trade_id, reasons_json,
                    evidence_json, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["audit_id"],
                    values["trade_plan_id"],
                    values["validation_id"],
                    values["signal_id"],
                    values["snapshot_id"],
                    values["instrument"],
                    values["planning_horizon"],
                    int(bool(values["policy_allowed"])),
                    int(bool(values["execution_eligible"])),
                    values["action"],
                    values["paper_trade_id"],
                    json.dumps(values["reasons"], sort_keys=True, default=str),
                    json.dumps(values["evidence"], sort_keys=True, default=str),
                    values["created_at"],
                    values["created_by"],
                ),
            )
        return record.audit_id

    def get(self, audit_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM execution_audits WHERE audit_id=?",
            (audit_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def latest_for_plan(self, trade_plan_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM execution_audits WHERE trade_plan_id=? "
            "ORDER BY created_at DESC, audit_id DESC LIMIT 1",
            (trade_plan_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def list(
        self,
        *,
        trade_plan_id: str | None = None,
        action: str | None = None,
        instrument: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM execution_audits WHERE 1=1"
        params: list[Any] = []
        if trade_plan_id:
            query += " AND trade_plan_id=?"
            params.append(trade_plan_id)
        if action:
            query += " AND action=?"
            params.append(action)
        if instrument:
            query += " AND instrument=?"
            params.append(instrument)
        query += " ORDER BY created_at DESC, audit_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        rows = self.connection.execute(query, params).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["policy_allowed"] = bool(item["policy_allowed"])
        item["execution_eligible"] = bool(item["execution_eligible"])
        item["reasons"] = json.loads(item.pop("reasons_json"))
        item["evidence"] = json.loads(item.pop("evidence_json"))
        return item
