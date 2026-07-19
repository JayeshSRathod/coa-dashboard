"""Append-only persistence boundary for validation and confidence evidence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.validation.models import ValidationResult

from .repository import SQLiteRepository


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


def _decode(row: dict[str, Any]) -> ValidationResult:
    return ValidationResult.new(
        validation_id=row["validation_id"], coa_result_id=row["coa_result_id"],
        snapshot_id=row["snapshot_id"], session_id=row["session_id"],
        experiment_id=row["experiment_id"], strategy_version=row["strategy_version"],
        validation_version=row["validation_version"], volume_score=row["volume_score"],
        oi_score=row["oi_score"], strike_score=row["strike_score"],
        liquidity_score=row["liquidity_score"], market_context_score=row["market_context_score"],
        historical_score=row["historical_score"], overall_score=row["overall_score"],
        confidence_band=row["confidence_band"], is_valid=bool(row["is_valid"]),
        failure_reasons=json.loads(row["failure_reasons_json"]),
        warning_reasons=json.loads(row["warning_reasons_json"]),
        scoring_details=json.loads(row["scoring_details_json"]),
        processing_time_ms=row["processing_time_ms"], created_at=row["created_at"],
        created_by=row["created_by"],
    )


class ValidationRepository(SQLiteRepository):
    """The only persistence boundary for validation results."""

    def append(self, result: ValidationResult) -> ValidationResult:
        experiment_key = result.experiment_id or ""
        existing = self.get_for_coa_result(
            result.coa_result_id, result.validation_version, result.experiment_id
        )
        if existing is not None:
            return existing
        values = (
            result.validation_id, result.coa_result_id, result.snapshot_id, result.session_id,
            result.experiment_id, experiment_key, result.strategy_version, result.validation_version,
            result.volume_score, result.oi_score, result.strike_score, result.liquidity_score,
            result.market_context_score, result.historical_score, result.overall_score,
            result.confidence_band, int(result.is_valid), _json(result.failure_reasons),
            _json(result.warning_reasons), _json(dict(result.scoring_details)),
            result.processing_time_ms, result.created_at, result.created_by,
        )
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO validation_results (
                        validation_id, coa_result_id, snapshot_id, session_id, experiment_id,
                        experiment_key, strategy_version, validation_version, volume_score, oi_score,
                        strike_score, liquidity_score, market_context_score, historical_score,
                        overall_score, confidence_band, is_valid, failure_reasons_json,
                        warning_reasons_json, scoring_details_json, processing_time_ms, created_at,
                        created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_coa_result(
                result.coa_result_id, result.validation_version, result.experiment_id
            )
            if existing is not None:
                return existing
            raise
        return result

    def get(self, validation_id: str) -> ValidationResult | None:
        row = self.connection.execute(
            "SELECT * FROM validation_results WHERE validation_id = ?", (validation_id,)
        ).fetchone()
        return _decode(dict(row)) if row else None

    def get_for_coa_result(
        self, coa_result_id: str, validation_version: str, experiment_id: str | None
    ) -> ValidationResult | None:
        row = self.connection.execute(
            "SELECT * FROM validation_results WHERE coa_result_id = ? "
            "AND validation_version = ? AND experiment_key = ?",
            (coa_result_id, validation_version, experiment_id or ""),
        ).fetchone()
        return _decode(dict(row)) if row else None

    def list_by_coa_result(self, coa_result_id: str) -> list[ValidationResult]:
        rows = self.connection.execute(
            "SELECT * FROM validation_results WHERE coa_result_id = ? "
            "ORDER BY created_at ASC, validation_id ASC", (coa_result_id,)
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def list_by_snapshot(self, snapshot_id: str) -> list[ValidationResult]:
        rows = self.connection.execute(
            "SELECT * FROM validation_results WHERE snapshot_id = ? "
            "ORDER BY created_at ASC, validation_id ASC", (snapshot_id,)
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def list_by_session(self, session_id: str) -> list[ValidationResult]:
        rows = self.connection.execute(
            "SELECT * FROM validation_results WHERE session_id = ? "
            "ORDER BY created_at ASC, validation_id ASC", (session_id,)
        ).fetchall()
        return [_decode(dict(row)) for row in rows]
