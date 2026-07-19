"""Append-only market provider registry repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .repository import SQLiteRepository


class MarketProviderRepository(SQLiteRepository):
    def register(self, provider_name: str, *, asset_classes: list[str], enabled: bool = True,
                 priority: int = 100, provider_id: str | None = None) -> str:
        provider_id = provider_id or str(uuid4())
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO market_providers VALUES (?, ?, ?, ?, ?, ?, ?)",
                (provider_id, provider_name, json.dumps(sorted(asset_classes)), int(enabled), priority,
                 datetime.now(timezone.utc).isoformat(), "MultiBrokerFramework"))
        row = self.connection.execute("SELECT provider_id FROM market_providers WHERE provider_name=?",
                                      (provider_name,)).fetchone()
        return row["provider_id"]

    def list_enabled(self):
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM market_providers WHERE enabled=1 ORDER BY priority, provider_name"
        ).fetchall()]
