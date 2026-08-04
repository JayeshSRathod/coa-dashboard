"""Append-only persistence for per-snapshot combined COA scenario tracks."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .repository import SQLiteRepository


class ScenarioTrackRepository(SQLiteRepository):
    """Store the baseline COA1 and observational COA2 tracks for replay."""

    def append(self, record: dict[str, Any]) -> str:
        columns = (
            "scenario_track_id", "snapshot_id", "session_id", "instrument", "coa_result_id",
            "structural_scenario_number", "structural_scenario", "tactical_scenario_number",
            "tactical_native_number", "tactical_action", "catalog_version", "payload_json", "created_at",
        )
        values = [
            json.dumps(record.get("payload", {}), sort_keys=True, default=str)
            if column == "payload_json" else record.get(column)
            for column in columns
        ]
        try:
            with self.connection:
                self.connection.execute(
                    f"INSERT INTO coa_scenario_tracks ({', '.join(columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})", values,
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_snapshot(str(record["snapshot_id"]), str(record["catalog_version"]))
            if existing is None:
                raise
            return str(existing["scenario_track_id"])
        return str(record["scenario_track_id"])

    def get_for_snapshot(self, snapshot_id: str, catalog_version: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM coa_scenario_tracks WHERE snapshot_id=? AND catalog_version=?",
            (snapshot_id, catalog_version),
        ).fetchone()
        return self._decode(row) if row else None

    def latest(self, instrument: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM coa_scenario_tracks WHERE instrument=? "
            "ORDER BY created_at DESC, scenario_track_id DESC LIMIT 1", (instrument,),
        ).fetchone()
        return self._decode(row) if row else None

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result
