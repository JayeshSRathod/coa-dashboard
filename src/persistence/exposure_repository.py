"""Append-only portfolio capital and exposure event store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .repository import SQLiteRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExposureRepository(SQLiteRepository):
    """Persist capital movements and portfolio exposure checkpoints."""

    def append_capital_event(
        self, *, portfolio_id: str, decision_id: str, event_type: str, amount: float,
        payload: dict[str, Any] | None = None, event_id: str | None = None, occurred_at: str | None = None,
    ) -> str:
        event_id = event_id or str(uuid4())
        occurred_at = occurred_at or _now()
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO portfolio_capital_events
                    (event_id, portfolio_id, decision_id, event_type, amount, occurred_at, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, portfolio_id, decision_id, event_type, float(amount), occurred_at,
                 json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str), _now()),
            )
        row = self.connection.execute(
            "SELECT event_id FROM portfolio_capital_events WHERE decision_id = ? AND event_type = ?",
            (decision_id, event_type),
        ).fetchone()
        return str(row["event_id"])

    def append_exposure(
        self, *, portfolio_id: str, source_snapshot_id: str | None, instrument: str | None,
        expiry: str | None, option_type: str | None, invested_amount: float, total_risk: float,
        open_positions: int, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0,
        total_equity: float = 0.0, max_drawdown: float = 0.0, payload: dict[str, Any] | None = None,
        exposure_id: str | None = None, created_at: str | None = None,
    ) -> str:
        exposure_id = exposure_id or str(uuid4())
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO portfolio_exposures (
                    exposure_id, portfolio_id, source_snapshot_id, instrument, expiry, option_type,
                    invested_amount, total_risk, open_positions, realized_pnl, unrealized_pnl,
                    total_equity, max_drawdown, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (exposure_id, portfolio_id, source_snapshot_id, instrument, expiry, option_type,
                 float(invested_amount), float(total_risk), int(open_positions), float(realized_pnl),
                 float(unrealized_pnl), float(total_equity), float(max_drawdown),
                 json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str),
                 created_at or _now()),
            )
        return exposure_id

    def latest(self, portfolio_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM portfolio_exposures WHERE portfolio_id = ? "
            "ORDER BY created_at DESC, exposure_id DESC LIMIT 1", (portfolio_id,)
        ).fetchone()
        return self._decode_exposure(row) if row else None

    def list_for_portfolio(self, portfolio_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM portfolio_exposures WHERE portfolio_id = ? ORDER BY created_at ASC, exposure_id ASC",
            (portfolio_id,),
        ).fetchall()
        return [self._decode_exposure(row) for row in rows]

    def capital_reserved(self, portfolio_id: str) -> float:
        row = self.connection.execute(
            "SELECT COALESCE(SUM(CASE WHEN event_type = 'CAPITAL_RESERVED' THEN amount "
            "WHEN event_type IN ('CAPITAL_RELEASED', 'PARTIAL_CAPITAL_RELEASED') THEN -amount ELSE 0 END), 0) "
            "AS value FROM portfolio_capital_events WHERE portfolio_id = ?",
            (portfolio_id,),
        ).fetchone()
        return float(row["value"])

    @staticmethod
    def _decode_exposure(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json") or "{}")
        return result
