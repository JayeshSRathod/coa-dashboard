"""Append-only persistence for dynamic option-wall states and research events."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from .repository import SQLiteRepository


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)


class StructureEventRepository(SQLiteRepository):
    """Repository-only boundary for the dynamic COA structure research layer."""

    def append_wall(self, wall: dict[str, Any]) -> str:
        wall_id = wall.get("wall_id") or str(uuid4())
        values = (
            wall_id, wall["snapshot_id"], wall["session_id"], wall["instrument"], wall.get("expiry"),
            wall["captured_at"], wall["side"], wall["metric"], wall["rank"],
            wall["strike"], wall["metric_value"], _json(wall.get("payload", {})),
        )
        try:
            with self.connection:
                self.connection.execute(
                    """INSERT INTO dynamic_option_walls (
                    wall_id, snapshot_id, session_id, instrument, expiry, captured_at, side,
                    metric, rank, strike, metric_value, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", values
                )
        except sqlite3.IntegrityError:
            row = self.connection.execute(
                "SELECT wall_id FROM dynamic_option_walls WHERE snapshot_id=? AND side=? AND metric=? AND rank=?",
                (wall["snapshot_id"], wall["side"], wall["metric"], wall["rank"]),
            ).fetchone()
            if row:
                return str(row["wall_id"])
            raise
        return str(wall_id)

    def append_event(self, event: dict[str, Any]) -> str:
        event_id = event.get("event_id") or str(uuid4())
        columns = (
            "event_id", "snapshot_id", "session_id", "instrument", "expiry", "occurred_at",
            "event_type", "event_key", "scenario_track", "coa1_scenario_number",
            "coa2_scenario_number", "coa_result_id", "validation_id", "signal_id",
            "risk_decision_id", "paper_trade_id", "outcome_state", "payload_json", "created_at",
        )
        values = [
            event_id if column == "event_id" else _json(event.get("payload", {}))
            if column == "payload_json" else event.get(column)
            for column in columns
        ]
        try:
            with self.connection:
                self.connection.execute(
                    f"INSERT INTO dynamic_structure_events ({', '.join(columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})", values,
                )
        except sqlite3.IntegrityError:
            row = self.connection.execute(
                "SELECT event_id FROM dynamic_structure_events WHERE snapshot_id=? AND event_type=? AND event_key=?",
                (event["snapshot_id"], event["event_type"], event["event_key"]),
            ).fetchone()
            if row:
                return str(row["event_id"])
            raise
        return str(event_id)

    def latest_walls(self, instrument: str, session_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT * FROM dynamic_option_walls WHERE instrument=? AND session_id=?
            AND captured_at=(SELECT MAX(captured_at) FROM dynamic_option_walls WHERE instrument=? AND session_id=?)
            ORDER BY side, metric, rank""", (instrument, session_id, instrument, session_id),
        ).fetchall()
        return [self._decode_wall(row) for row in rows]

    def list_events(self, instrument: str, *, session_id: str | None = None,
                    event_types: tuple[str, ...] = (), limit: int = 10_000) -> list[dict[str, Any]]:
        query = (
            "SELECT e.*, COALESCE(e.expiry, s.expiry) AS resolved_expiry "
            "FROM dynamic_structure_events e LEFT JOIN market_snapshots s ON s.snapshot_id=e.snapshot_id "
            "WHERE e.instrument=?"
        )
        values: list[Any] = [instrument]
        if session_id:
            query += " AND e.session_id=?"
            values.append(session_id)
        if event_types:
            query += " AND e.event_type IN (" + ",".join("?" for _ in event_types) + ")"
            values.extend(event_types)
        rows = self.connection.execute(
            query + " ORDER BY occurred_at DESC, event_id DESC LIMIT ?",
            [*values, max(1, min(int(limit), 25_000))],
        ).fetchall()
        return [self._decode_event(row) for row in rows]

    def list_walls(self, instrument: str, *, session_id: str | None = None,
                   limit: int = 25_000) -> list[dict[str, Any]]:
        query = (
            "SELECT w.*, COALESCE(w.expiry, s.expiry) AS resolved_expiry "
            "FROM dynamic_option_walls w LEFT JOIN market_snapshots s ON s.snapshot_id=w.snapshot_id "
            "WHERE w.instrument=?"
        )
        values: list[Any] = [instrument]
        if session_id:
            query += " AND w.session_id=?"
            values.append(session_id)
        rows = self.connection.execute(
            query + " ORDER BY captured_at ASC, side ASC, metric ASC, rank ASC LIMIT ?",
            [*values, max(1, min(int(limit), 50_000))],
        ).fetchall()
        return [self._decode_wall(row) for row in rows]

    def list_sessions(self, instrument: str) -> list[str]:
        rows = self.connection.execute(
            "SELECT DISTINCT session_id FROM dynamic_structure_events WHERE instrument=? ORDER BY session_id DESC",
            (instrument,),
        ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def list_event_types(self, instrument: str, session_id: str | None = None) -> list[str]:
        query = "SELECT DISTINCT event_type FROM dynamic_structure_events WHERE instrument=?"
        values: list[Any] = [instrument]
        if session_id:
            query += " AND session_id=?"
            values.append(session_id)
        rows = self.connection.execute(query + " ORDER BY event_type", values).fetchall()
        return [str(row["event_type"]) for row in rows]

    @staticmethod
    def _decode_wall(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["expiry"] = item.pop("resolved_expiry", None) or item.get("expiry")
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    @staticmethod
    def _decode_event(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["expiry"] = item.pop("resolved_expiry", None) or item.get("expiry")
        item["payload"] = json.loads(item.pop("payload_json"))
        return item
