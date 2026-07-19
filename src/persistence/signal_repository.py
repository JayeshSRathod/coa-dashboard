"""Append-only persistence boundary for immutable research signal recommendations."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.signal.models import ResearchSignal

from .repository import SQLiteRepository


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


def _decode(row: dict[str, Any]) -> ResearchSignal:
    return ResearchSignal.new(
        signal_id=row["signal_id"], snapshot_id=row["snapshot_id"],
        coa_result_id=row["coa_result_id"], validation_id=row["validation_id"],
        session_id=row["session_id"], experiment_id=row["experiment_id"],
        strategy_version=row["strategy_version"], signal_version=row["signal_version"],
        instrument=row["instrument"], expiry=row["expiry"], signal_type=row["signal_type"],
        signal_state=row["signal_state"], direction=row["direction"], entry_price=row["entry_price"],
        stop_loss=row["stop_loss"], target_1=row["target_1"], target_2=row["target_2"],
        trailing_reference=row["trailing_reference"], confidence_score=row["confidence_score"],
        confidence_band=row["confidence_band"], scenario=row["scenario"], eos=row["eos"], eor=row["eor"],
        momentum=json.loads(row["momentum_json"]) if row["momentum_json"] else None,
        diversion=json.loads(row["diversion_json"]) if row["diversion_json"] else None,
        reasons=json.loads(row["reasons_json"]), warnings=json.loads(row["warnings_json"]),
        details=json.loads(row["details_json"]), processing_time_ms=row["processing_time_ms"],
        created_at=row["created_at"], created_by=row["created_by"],
    )


class SignalRepository(SQLiteRepository):
    """Repository for research recommendations; no execution code is permitted here."""

    def insert_signal(self, signal: ResearchSignal) -> ResearchSignal:
        experiment_key = signal.experiment_id or ""
        existing = self.get_for_validation(
            signal.validation_id, signal.signal_version, signal.experiment_id
        )
        if existing is not None:
            return existing
        values = (
            signal.signal_id, signal.snapshot_id, signal.coa_result_id, signal.validation_id,
            signal.session_id, signal.experiment_id, experiment_key, signal.strategy_version,
            signal.signal_version, signal.instrument, signal.expiry, signal.signal_type,
            signal.signal_state, signal.direction, signal.entry_price, signal.stop_loss,
            signal.target_1, signal.target_2, signal.trailing_reference, signal.confidence_score,
            signal.confidence_band, signal.scenario, signal.eos, signal.eor,
            _json(dict(signal.momentum)) if signal.momentum is not None else None,
            _json(dict(signal.diversion)) if signal.diversion is not None else None,
            _json(signal.reasons), _json(signal.warnings), _json(dict(signal.details)),
            signal.processing_time_ms, signal.created_at, signal.created_by,
        )
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO research_signals (
                        signal_id, snapshot_id, coa_result_id, validation_id, session_id,
                        experiment_id, experiment_key, strategy_version, signal_version, instrument,
                        expiry, signal_type, signal_state, direction, entry_price, stop_loss,
                        target_1, target_2, trailing_reference, confidence_score, confidence_band,
                        scenario, eos, eor, momentum_json, diversion_json, reasons_json,
                        warnings_json, details_json, processing_time_ms, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_validation(
                signal.validation_id, signal.signal_version, signal.experiment_id
            )
            if existing is not None:
                return existing
            raise
        return signal

    def get_signal(self, signal_id: str) -> ResearchSignal | None:
        row = self.connection.execute(
            "SELECT * FROM research_signals WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        return _decode(dict(row)) if row else None

    def get_active_signals(self, session_id: str | None = None) -> list[ResearchSignal]:
        sql = "SELECT * FROM research_signals WHERE signal_state = 'ACTIVE'"
        parameters: tuple[Any, ...] = ()
        if session_id:
            sql += " AND session_id = ?"
            parameters = (session_id,)
        rows = self.connection.execute(sql + " ORDER BY created_at ASC, signal_id ASC", parameters).fetchall()
        return [_decode(dict(row)) for row in rows]

    def get_session_signals(self, session_id: str) -> list[ResearchSignal]:
        rows = self.connection.execute(
            "SELECT * FROM research_signals WHERE session_id = ? ORDER BY created_at ASC, signal_id ASC",
            (session_id,),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def get_snapshot_signal(self, snapshot_id: str) -> list[ResearchSignal]:
        rows = self.connection.execute(
            "SELECT * FROM research_signals WHERE snapshot_id = ? ORDER BY created_at ASC, signal_id ASC",
            (snapshot_id,),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def get_signals_by_confidence(self, minimum_confidence: float) -> list[ResearchSignal]:
        rows = self.connection.execute(
            "SELECT * FROM research_signals WHERE confidence_score >= ? "
            "ORDER BY confidence_score DESC, created_at ASC, signal_id ASC",
            (float(minimum_confidence),),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def get_for_validation(
        self, validation_id: str, signal_version: str, experiment_id: str | None
    ) -> ResearchSignal | None:
        row = self.connection.execute(
            "SELECT * FROM research_signals WHERE validation_id = ? AND signal_version = ? "
            "AND experiment_key = ?", (validation_id, signal_version, experiment_id or "")
        ).fetchone()
        return _decode(dict(row)) if row else None
