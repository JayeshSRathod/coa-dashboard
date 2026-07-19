"""Dedicated repository for immutable market snapshots and replay reads."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from src.research.models import CapturedSnapshot
from src.research.validation import SnapshotValidationResult

from .repository import SQLiteRepository


_INSERT_SNAPSHOT_SQL = """
    INSERT INTO market_snapshots (
        snapshot_id, captured_at, instrument, spot, market_source,
        scenario_number, scenario, risk_mode, support, resistance, eos, eor,
        coa_payload_json, option_chain_json, data_quality_status, source_latency_ms,
        session_id, market_captured_at, ingested_at, futures_price, atm_strike,
        expiry, expiry_type, data_completeness, is_complete,
        missing_strikes_json, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("coa_payload_json", "option_chain_json", "missing_strikes_json", "metadata_json"):
        if row.get(key) is not None:
            row[key.removesuffix("_json")] = json.loads(row[key])
    return row


def _row(snapshot: CapturedSnapshot, validation: SnapshotValidationResult) -> tuple[Any, ...]:
    return (
        snapshot.snapshot_id, snapshot.market_captured_at, snapshot.instrument, snapshot.spot,
        snapshot.source, snapshot.coa_payload.get("scenario_number"),
        snapshot.coa_payload.get("scenario"), snapshot.coa_payload.get("risk_mode"),
        snapshot.coa_payload.get("support"), snapshot.coa_payload.get("resistance"),
        snapshot.coa_payload.get("eos"), snapshot.coa_payload.get("eor"),
        _json(snapshot.coa_payload), _json(snapshot.option_chain),
        "VALID" if validation.is_complete else "DEGRADED", snapshot.source_latency_ms,
        snapshot.session_id, snapshot.market_captured_at, snapshot.ingested_at,
        snapshot.futures_price, snapshot.atm_strike, snapshot.expiry, snapshot.expiry_type,
        validation.data_completeness, int(validation.is_complete),
        _json(list(validation.missing_strikes)), _json(snapshot.metadata),
    )


class SnapshotRepository(SQLiteRepository):
    """The only persistence boundary used by snapshot collection and replay."""

    def append(self, snapshot: CapturedSnapshot, validation: SnapshotValidationResult) -> str:
        with self.connection:
            self.connection.execute(_INSERT_SNAPSHOT_SQL, _row(snapshot, validation))
        return snapshot.snapshot_id

    def append_batch(
        self,
        items: list[tuple[CapturedSnapshot, SnapshotValidationResult]],
    ) -> list[str]:
        """Atomically write a validated batch in one database transaction."""
        if not items:
            return []
        with self.connection:
            self.connection.executemany(
                _INSERT_SNAPSHOT_SQL, [_row(snapshot, validation) for snapshot, validation in items]
            )
        return [snapshot.snapshot_id for snapshot, _ in items]

    def get(self, snapshot_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM market_snapshots WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()
        return _decode(dict(row)) if row else None

    def get_latest_snapshot(self, instrument: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM market_snapshots WHERE instrument = ? "
            "ORDER BY market_captured_at DESC LIMIT 1",
            (instrument,),
        ).fetchone()
        return _decode(dict(row)) if row else None

    def list_by_session(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM market_snapshots WHERE session_id = ? "
            "ORDER BY market_captured_at ASC, snapshot_id ASC",
            (session_id,),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def list_by_time_range(self, instrument: str, start: str, end: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM market_snapshots WHERE instrument = ? "
            "AND market_captured_at >= ? AND market_captured_at <= ? "
            "ORDER BY market_captured_at ASC, snapshot_id ASC",
            (instrument, start, end),
        ).fetchall()
        return [_decode(dict(row)) for row in rows]

    def record_event(
        self,
        event_type: str,
        severity: str,
        payload: dict[str, Any],
        instrument: str | None = None,
        occurred_at: str | None = None,
    ) -> str:
        event_id = str(uuid4())
        occurred_at = occurred_at or datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO system_events VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, occurred_at, event_type, severity, instrument, _json(payload)),
            )
        return event_id

    def list_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        if event_type:
            rows = self.connection.execute(
                "SELECT * FROM system_events WHERE event_type = ? ORDER BY occurred_at ASC",
                (event_type,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM system_events ORDER BY occurred_at ASC"
            ).fetchall()
        return [dict(row) for row in rows]
