"""Append-only persistence for CQRP plan revalidation results."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.premarket_validation.models import PreMarketValidationResult

from .repository import SQLiteRepository


def install_premarket_validation_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS premarket_validations (
            validation_id TEXT PRIMARY KEY,
            trade_plan_id TEXT NOT NULL,
            source_snapshot_id TEXT NOT NULL,
            observed_snapshot_id TEXT NOT NULL,
            planning_horizon TEXT NOT NULL,
            validation_result TEXT NOT NULL,
            selected_plan TEXT,
            opening_classification TEXT NOT NULL,
            confidence_before REAL NOT NULL,
            confidence_after REAL NOT NULL,
            risk_status TEXT NOT NULL,
            data_quality TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            validator_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(trade_plan_id, observed_snapshot_id, validator_version),
            FOREIGN KEY(trade_plan_id) REFERENCES trade_plans(trade_plan_id)
        );

        CREATE INDEX IF NOT EXISTS idx_premarket_validation_plan_time
            ON premarket_validations(trade_plan_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_premarket_validation_result_time
            ON premarket_validations(validation_result, created_at);
        CREATE INDEX IF NOT EXISTS idx_premarket_validation_horizon_time
            ON premarket_validations(planning_horizon, created_at);

        CREATE TRIGGER IF NOT EXISTS premarket_validations_no_update
            BEFORE UPDATE ON premarket_validations BEGIN
            SELECT RAISE(ABORT, 'premarket_validations is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS premarket_validations_no_delete
            BEFORE DELETE ON premarket_validations BEGIN
            SELECT RAISE(ABORT, 'premarket_validations is append-only');
            END;
        """
    )


class PreMarketValidationRepository(SQLiteRepository):
    """Persistence boundary for immutable revalidation outcomes."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_premarket_validation_schema(connection)

    def append(self, result: PreMarketValidationResult) -> str:
        values = result.as_dict()
        columns = (
            "validation_id", "trade_plan_id", "source_snapshot_id",
            "observed_snapshot_id", "planning_horizon", "validation_result",
            "selected_plan", "opening_classification", "confidence_before",
            "confidence_after", "risk_status", "data_quality", "reasons_json",
            "warnings_json", "evidence_json", "validator_version", "created_at",
            "created_by",
        )
        row: list[Any] = []
        for column in columns:
            source = column.removesuffix("_json")
            value = values.get(source)
            row.append(json.dumps(value, sort_keys=True, default=str) if column.endswith("_json") else value)
        try:
            with self.connection:
                self.connection.execute(
                    f"INSERT INTO premarket_validations ({', '.join(columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})",
                    row,
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_observation(
                result.trade_plan_id,
                result.observed_snapshot_id,
                result.validator_version,
            )
            if existing is not None:
                return str(existing["validation_id"])
            raise
        return result.validation_id

    def get(self, validation_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM premarket_validations WHERE validation_id=?",
            (validation_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def get_for_observation(
        self,
        trade_plan_id: str,
        observed_snapshot_id: str,
        validator_version: str,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM premarket_validations "
            "WHERE trade_plan_id=? AND observed_snapshot_id=? AND validator_version=?",
            (trade_plan_id, observed_snapshot_id, validator_version),
        ).fetchone()
        return self._decode(row) if row else None

    def latest_for_plan(self, trade_plan_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM premarket_validations WHERE trade_plan_id=? "
            "ORDER BY created_at DESC, validation_id DESC LIMIT 1",
            (trade_plan_id,),
        ).fetchone()
        return self._decode(row) if row else None

    def list(
        self,
        *,
        trade_plan_id: str | None = None,
        planning_horizon: str | None = None,
        validation_result: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM premarket_validations WHERE 1=1"
        params: list[Any] = []
        if trade_plan_id:
            query += " AND trade_plan_id=?"
            params.append(trade_plan_id)
        if planning_horizon:
            query += " AND planning_horizon=?"
            params.append(planning_horizon)
        if validation_result:
            query += " AND validation_result=?"
            params.append(validation_result)
        query += " ORDER BY created_at DESC, validation_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        rows = self.connection.execute(query, params).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["reasons"] = json.loads(item.pop("reasons_json"))
        item["warnings"] = json.loads(item.pop("warnings_json"))
        item["evidence"] = json.loads(item.pop("evidence_json"))
        return item
