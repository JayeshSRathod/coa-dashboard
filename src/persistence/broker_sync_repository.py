"""Append-only audit store for broker synchronization evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .repository import SQLiteRepository


class BrokerSyncRepository(SQLiteRepository):
    def append(self, *, broker_name: str, sync_type: str, status: str, payload: dict,
               sync_id: str | None = None, occurred_at: str | None = None) -> str:
        sync_id = sync_id or str(uuid4())
        occurred_at = occurred_at or datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO broker_sync_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sync_id, broker_name, sync_type, status,
                 json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
                 occurred_at, datetime.now(timezone.utc).isoformat()),
            )
        return sync_id
