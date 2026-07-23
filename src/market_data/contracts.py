"""Provider contracts. Implementations emit CQRP models, never broker JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import MarketQuote, OptionChainSnapshot, ProviderHealth


@dataclass(frozen=True)
class OptionChainRequest:
    instrument_id: str
    symbol: str
    expiry: str
    strike_count: int = 10
    security_id: int | None = None
    segment: str | None = None


class MarketDataProvider(Protocol):
    name: str

    def fetch_option_chain(self, request: OptionChainRequest) -> OptionChainSnapshot: ...
    def fetch_quote(self, instrument_id: str, symbol: str) -> MarketQuote: ...
    def health(self) -> ProviderHealth: ...
