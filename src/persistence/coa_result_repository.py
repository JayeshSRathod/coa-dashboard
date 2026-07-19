"""Append-only repository for typed COA research-engine results."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.coa.models import COAResearchResult

from .repository import SQLiteRepository


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


def _decode(row: dict[str, Any]) -> COAResearchResult:
    return COAResearchResult.new(
        coa_result_id=row["coa_result_id"],
        snapshot_id=row["snapshot_id"],
        session_id=row["session_id"],
        experiment_id=row["experiment_id"],
        strategy_version=row["strategy_version"],
        engine_version=row["engine_version"],
        scenario_number=row["scenario_number"],
        scenario=row["scenario"],
        eos=row["eos"], eor=row["eor"], support=row["support"], resistance=row["resistance"],
        momentum=json.loads(row["momentum_json"]) if row["momentum_json"] else None,
        diversion=json.loads(row["diversion_json"]) if row["diversion_json"] else None,
        trend=row["trend"], direction=row["direction"], risk_mode=row["risk_mode"],
        raw_output=json.loads(row["raw_output_json"]),
        processing_time_ms=row["processing_time_ms"],
        market_timestamp=row["market_timestamp"], created_at=row["created_at"],
        created_by=row["created_by"],
    )


class COAResultRepository(SQLiteRepository):
    """The only persistence boundary for immutable COA research outputs."""

    def append(self, result: COAResearchResult) -> COAResearchResult:
        """Persist once per snapshot, engine, and experiment; return stored result."""
        experiment_key = result.experiment_id or ""
        existing = self.get_for_snapshot_engine(
            result.snapshot_id, result.engine_version, result.experiment_id
        )
        if existing is not None:
            return existing
        values = (
            result.coa_result_id, result.snapshot_id, result.session_id, result.experiment_id,
            experiment_key, result.strategy_version, result.engine_version,
            result.scenario_number, result.scenario, result.eos, result.eor, result.support,
            result.resistance,
            _json(dict(result.momentum)) if result.momentum is not None else None,
            _json(dict(result.diversion)) if result.diversion is not None else None,
            result.trend, result.direction, result.risk_mode, _json(dict(result.raw_output)),
            result.processing_time_ms, result.market_timestamp, result.created_at, result.created_by,
        )
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO coa_results (
                        coa_result_id, snapshot_id, session_id, experiment_id, experiment_key,
                        strategy_version, engine_version, scenario_number, scenario, eos, eor,
                        support, resistance, momentum_json, diversion_json, trend, direction,
                        risk_mode, raw_output_json, processing_time_ms, market_timestamp,
                        created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_snapshot_engine(
                result.snapshot_id, result.engine_version, result.experiment_id
            )
            if existing is not None:
                return existing
            raise
        return result

    def get(self, coa_result_id: str) -> COAResearchResult | None:
        row = self.connection.execute(
            "SELECT * FROM coa_results WHERE coa_result_id = ?", (coa_result_id,)
        ).fetchone()
        return _decode(dict(row)) if row else None

    def get_for_snapshot_engine(
        self, snapshot_id: str, engine_version: str, experiment_id: str | None
    ) -> COAResearchResult | None:
        row = self.connection.execute(
            "SELECT * FROM coa_results WHERE snapshot_id = ? AND engine_version = ? "
            "AND experiment_key = ?", (snapshot_id, engine_version, experiment_id or "")
        ).fetchone()
        return _decode(dict(row)) if row else None

    def list_by_snapshot(self, snapshot_id: str) -> list[COAResearchResult]:
        rows = self.connection.execute(
            "SELECT * FROM coa_results WHERE snapshot_id = ? ORDER BY created_at ASC, coa_result_id ASC",
            (snapshot_id,),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def list_by_session(self, session_id: str) -> list[COAResearchResult]:
        rows = self.connection.execute(
            "SELECT * FROM coa_results WHERE session_id = ? "
            "ORDER BY market_timestamp ASC, coa_result_id ASC", (session_id,)
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def list_by_time_range(self, session_id: str, start: str, end: str) -> list[COAResearchResult]:
        rows = self.connection.execute(
            "SELECT * FROM coa_results WHERE session_id = ? AND market_timestamp >= ? "
            "AND market_timestamp <= ? ORDER BY market_timestamp ASC, coa_result_id ASC",
            (session_id, start, end),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]
