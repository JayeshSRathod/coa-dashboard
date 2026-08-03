"""Append-only persistence for CQRP next-session trade plans.

The repository owns storage only. It does not calculate a plan, change a plan,
place an order, or approve execution. Lifecycle changes are appended as events.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .repository import SQLiteRepository
from src.trade_planning.models import OpeningPlan, TradePlan


def install_trade_plan_schema(connection: sqlite3.Connection) -> None:
    """Install Sprint-201 schema until folded into the ordered master migration."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS trade_plans (
            trade_plan_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            signal_id TEXT,
            risk_decision_id TEXT,
            instrument TEXT NOT NULL,
            expiry TEXT,
            planning_horizon TEXT NOT NULL,
            market_bias TEXT NOT NULL,
            expected_opening TEXT NOT NULL,
            direction TEXT,
            option_type TEXT,
            entry REAL,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            confidence_score REAL NOT NULL,
            readiness TEXT NOT NULL,
            status TEXT NOT NULL,
            valid_for_session TEXT,
            rationale_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            opening_plans_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            planner_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(snapshot_id, planner_version)
        );
        CREATE INDEX IF NOT EXISTS idx_trade_plans_instrument_time
            ON trade_plans(instrument, created_at);
        CREATE INDEX IF NOT EXISTS idx_trade_plans_status_time
            ON trade_plans(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_trade_plans_signal
            ON trade_plans(signal_id);

        CREATE TABLE IF NOT EXISTS trade_plan_events (
            event_id TEXT PRIMARY KEY,
            trade_plan_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(trade_plan_id) REFERENCES trade_plans(trade_plan_id)
        );
        CREATE INDEX IF NOT EXISTS idx_trade_plan_events_plan_time
            ON trade_plan_events(trade_plan_id, occurred_at);

        CREATE TRIGGER IF NOT EXISTS trade_plans_no_update
            BEFORE UPDATE ON trade_plans BEGIN
            SELECT RAISE(ABORT, 'trade_plans is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS trade_plans_no_delete
            BEFORE DELETE ON trade_plans BEGIN
            SELECT RAISE(ABORT, 'trade_plans is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS trade_plan_events_no_update
            BEFORE UPDATE ON trade_plan_events BEGIN
            SELECT RAISE(ABORT, 'trade_plan_events is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS trade_plan_events_no_delete
            BEFORE DELETE ON trade_plan_events BEGIN
            SELECT RAISE(ABORT, 'trade_plan_events is append-only');
            END;
        """
    )


class TradePlanRepository(SQLiteRepository):
    """Persistence boundary for immutable next-session plans and lifecycle events."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_trade_plan_schema(connection)

    def append(self, plan: TradePlan) -> str:
        values = plan.as_dict()
        columns = (
            "trade_plan_id", "snapshot_id", "signal_id", "risk_decision_id",
            "instrument", "expiry", "planning_horizon", "market_bias",
            "expected_opening", "direction", "option_type", "entry", "stop_loss",
            "target_1", "target_2", "confidence_score", "readiness", "status",
            "valid_for_session", "rationale_json", "warnings_json",
            "opening_plans_json", "evidence_json", "planner_version", "created_at",
            "created_by",
        )
        row = []
        for column in columns:
            source = column.removesuffix("_json")
            value = values.get(source)
            row.append(json.dumps(value, sort_keys=True, default=str) if column.endswith("_json") else value)
        try:
            with self.connection:
                self.connection.execute(
                    f"INSERT INTO trade_plans ({', '.join(columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})", row,
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_snapshot(plan.snapshot_id, plan.planner_version)
            if existing is not None:
                return str(existing["trade_plan_id"])
            raise
        return plan.trade_plan_id

    def append_event(self, event: dict[str, Any]) -> str:
        columns = (
            "event_id", "trade_plan_id", "event_type", "from_status", "to_status",
            "occurred_at", "payload_json", "created_by",
        )
        values = [
            json.dumps(event.get("payload", {}), sort_keys=True, default=str)
            if column == "payload_json" else event.get(column)
            for column in columns
        ]
        with self.connection:
            self.connection.execute(
                f"INSERT INTO trade_plan_events ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})", values,
            )
        return str(event["event_id"])

    def get(self, trade_plan_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM trade_plans WHERE trade_plan_id=?", (trade_plan_id,)
        ).fetchone()
        return self._decode(row) if row else None

    def get_for_snapshot(self, snapshot_id: str, planner_version: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM trade_plans WHERE snapshot_id=? AND planner_version=?",
            (snapshot_id, planner_version),
        ).fetchone()
        return self._decode(row) if row else None

    def latest(self, instrument: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM trade_plans WHERE instrument=? "
            "ORDER BY created_at DESC, trade_plan_id DESC LIMIT 1", (instrument,),
        ).fetchone()
        return self._decode(row) if row else None

    def list(self, *, instrument: str | None = None, readiness: str | None = None,
             limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM trade_plans WHERE 1=1"
        values: list[Any] = []
        if instrument:
            query += " AND instrument=?"
            values.append(instrument)
        if readiness:
            query += " AND readiness=?"
            values.append(readiness)
        rows = self.connection.execute(
            query + " ORDER BY created_at DESC, trade_plan_id DESC LIMIT ?",
            [*values, max(1, min(int(limit), 1000))],
        ).fetchall()
        return [self._decode(row) for row in rows]

    def events(self, trade_plan_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM trade_plan_events WHERE trade_plan_id=? "
            "ORDER BY occurred_at ASC, event_id ASC", (trade_plan_id,),
        ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            output.append(item)
        return output

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["rationale"] = json.loads(item.pop("rationale_json"))
        item["warnings"] = json.loads(item.pop("warnings_json"))
        item["opening_plans"] = json.loads(item.pop("opening_plans_json"))
        item["evidence"] = json.loads(item.pop("evidence_json"))
        return item
