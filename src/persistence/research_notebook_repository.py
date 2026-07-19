"""Append-only searchable experiment notebook repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4
from .repository import SQLiteRepository


class ResearchNotebookRepository(SQLiteRepository):
    def append(self, *, experiment_id, entry_type, content, entry_id=None):
        entry_id = entry_id or str(uuid4())
        with self.connection:
            self.connection.execute("INSERT INTO research_notebook_entries VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, experiment_id, entry_type, json.dumps(content, sort_keys=True, default=str),
                 datetime.now(timezone.utc).isoformat(), "StrategyLab"))
        return entry_id

    def list_for_experiment(self, experiment_id):
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM research_notebook_entries WHERE experiment_id=? ORDER BY created_at, entry_id",
            (experiment_id,)).fetchall()]
