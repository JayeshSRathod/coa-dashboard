"""Append-only repository APIs for CQRP research data."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any
from uuid import uuid4

from .repository import SQLiteRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


class ResearchRepository(SQLiteRepository):
    """Writes immutable observations; later lifecycle state is a new event."""

    def register_strategy_profile(
        self,
        name: str,
        coa_engine_version: str,
        validation_engine_version: str,
        configuration: dict[str, Any],
        description: str | None = None,
        profile_id: str | None = None,
    ) -> str:
        profile_id = profile_id or str(uuid4())
        with self.connection:
            self.connection.execute(
                "INSERT INTO strategy_profiles VALUES (?, ?, ?, ?, ?, ?, ?)",
                (profile_id, name, coa_engine_version, validation_engine_version,
                 _json(configuration), _utc_now(), description),
            )
        return profile_id

    def append_snapshot(self, record: dict[str, Any]) -> str:
        snapshot_id = record.get("snapshot_id", str(uuid4()))
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO market_snapshots (
                    snapshot_id, captured_at, instrument, spot, market_source,
                    strategy_profile_id, scenario_number, scenario, risk_mode,
                    support, resistance, eos, eor, coa_payload_json,
                    option_chain_json, data_quality_status, source_latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id, record.get("captured_at", _utc_now()), record["instrument"],
                    record["spot"], record["market_source"], record.get("strategy_profile_id"),
                    record.get("scenario_number"), record.get("scenario"), record.get("risk_mode"),
                    record.get("support"), record.get("resistance"), record.get("eos"),
                    record.get("eor"), _json(record.get("coa_payload", {})),
                    _json(record["option_chain"]) if record.get("option_chain") is not None else None,
                    record.get("data_quality_status", "UNKNOWN"), record.get("source_latency_ms"),
                ),
            )
        return snapshot_id

    def record_signal(self, record: dict[str, Any]) -> str:
        signal_id = record.get("signal_id", str(uuid4()))
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id, record["snapshot_id"], record.get("created_at", _utc_now()),
                    record["instrument"], record["direction"], record["action"],
                    record.get("suggested_strike"), record.get("entry_level"),
                    record.get("stop_level"), record.get("target_level"),
                    record.get("confidence_score"), int(bool(record["trade_allowed"])),
                    record.get("strategy_profile_id"), _json(record.get("rationale", {})),
                ),
            )
        return signal_id

    def record_validation(self, record: dict[str, Any]) -> str:
        validation_id = record.get("validation_id", str(uuid4()))
        with self.connection:
            self.connection.execute(
                "INSERT INTO signal_validations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    validation_id, record["signal_id"], record.get("checked_at", _utc_now()),
                    record["category"], record.get("score"), int(bool(record["passed"])),
                    _json(record.get("reasons", [])),
                ),
            )
        return validation_id

    def record_system_event(self, event_type: str, severity: str, payload: dict[str, Any],
                            instrument: str | None = None, occurred_at: str | None = None) -> str:
        event_id = str(uuid4())
        with self.connection:
            self.connection.execute(
                "INSERT INTO system_events VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, occurred_at or _utc_now(), event_type, severity, instrument, _json(payload)),
            )
        return event_id

    def list_snapshots(self, instrument: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM market_snapshots WHERE instrument = ? "
            "ORDER BY captured_at DESC LIMIT ?",
            (instrument, limit),
        ).fetchall()
        return [dict(row) for row in rows]
