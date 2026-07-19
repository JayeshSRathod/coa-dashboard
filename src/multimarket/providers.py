"""Market-data provider contracts independent of broker transports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def snapshot(self, instrument_id: str) -> dict[str, Any]:
        """Return CQRP-normalized source data for an internal instrument."""


class CallableMarketDataProvider(MarketDataProvider):
    def __init__(self, name: str, loader) -> None:
        self.name, self.loader = name, loader

    def snapshot(self, instrument_id: str) -> dict[str, Any]:
        return dict(self.loader(instrument_id))


class UnsupportedMarketDataProvider(MarketDataProvider):
    def __init__(self, name: str) -> None:
        self.name = name

    def snapshot(self, instrument_id: str) -> dict[str, Any]:
        raise NotImplementedError(f"{self.name} market-data provider is a framework placeholder")
