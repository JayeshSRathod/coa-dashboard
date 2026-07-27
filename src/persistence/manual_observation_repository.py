"""Append-only repository for operator market observations.

Manual observations are research evidence.  They never alter a snapshot, COA
result, validation, signal, or paper-trade event.
"""

from __future__ import annotations

import json
from typing import Any

from .repository import SQLiteRepository


class ManualObservationRepository(SQLiteRepository):
    """Persistence boundary for evening/session review notes."""

    def append(self, observation: dict[str, Any]) -> str:
        columns = (
            "observation_id", "observed_at", "session_date", "instrument",
            "event_type", "scenario_number", "scenario_name", "spot",
            "support", "resistance", "eos", "eor", "narrative",
            "expected_outcome", "actual_outcome", "reference_text",
            "metadata_json", "created_at", "created_by", "source",
        )
        values = [
            observation.get(column) if column != "metadata_json" else json.dumps(
                observation.get("metadata", {}), sort_keys=True, default=str
            )
            for column in columns
        ]
        with self.connection:
            self.connection.execute(
                f"INSERT INTO manual_observations ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
        return str(observation["observation_id"])

    def list(self, *, instrument: str | None = None, session_date: str | None = None,
             limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM manual_observations WHERE 1=1"
        values: list[Any] = []
        if instrument:
            query += " AND instrument = ?"
            values.append(instrument)
        if session_date:
            query += " AND session_date = ?"
            values.append(session_date)
        rows = self.connection.execute(
            query + " ORDER BY observed_at DESC, observation_id DESC LIMIT ?",
            [*values, max(1, min(int(limit), 500))],
        ).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        return item
