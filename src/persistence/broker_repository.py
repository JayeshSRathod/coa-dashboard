"""Append-only broker registry repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .repository import SQLiteRepository


class BrokerRepository(SQLiteRepository):
    def register(self, broker_name: str, *, status: str = "ACTIVE", capabilities: dict | None = None,
                 broker_id: str | None = None) -> str:
        broker_id = broker_id or str(uuid4())
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO brokers VALUES (?, ?, ?, ?, ?, ?)",
                (broker_id, broker_name, status, json.dumps(capabilities or {}, sort_keys=True),
                 datetime.now(timezone.utc).isoformat(), "MultiBrokerFramework"),
            )
        row = self.connection.execute("SELECT broker_id FROM brokers WHERE broker_name=?", (broker_name,)).fetchone()
        return row["broker_id"]

    def get(self, broker_name: str):
        row = self.connection.execute("SELECT * FROM brokers WHERE broker_name=?", (broker_name,)).fetchone()
        return {**dict(row), "capabilities": json.loads(row["capabilities_json"])} if row else None
