"""Read-only application service backing future HTTP endpoints and workstations."""

from __future__ import annotations

from typing import Any

from src.persistence.market_data_repository import MarketDataRepository


class MarketReadService:
    """Serializable read contract: /system, /provider, /market, /snapshot."""

    api_version = "v1"

    def __init__(self, repository: MarketDataRepository) -> None:
        self.repository = repository

    def system(self) -> dict[str, Any]:
        return {"api_version": self.api_version, "execution_mode": "DISABLED", "read_only": True}

    def provider(self, name: str | None = None) -> dict[str, Any]:
        return {"providers": self.repository.latest_health(name)}

    def market(self, instrument_id: str) -> dict[str, Any]:
        return {"instrument_id": instrument_id, "snapshot": self.repository.latest_snapshot(instrument_id)}

    def snapshot(self, instrument_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        return {"instrument_id": instrument_id, "snapshots": self.repository.list_snapshots(instrument_id, start, end)}
