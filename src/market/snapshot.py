"""Provider-neutral market snapshot input contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class MarketSnapshotPayload:
    """Normalized provider output before CQRP validation and persistence."""

    instrument: str
    spot: float
    source: str
    option_chain: list[dict[str, Any]]
    market_captured_at: str | None = None
    session_id: str | None = None
    futures_price: float | None = None
    atm_strike: float | None = None
    expiry: str | None = None
    expiry_type: str | None = None
    source_latency_ms: int | None = None
    coa_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class MarketSnapshotProvider(Protocol):
    """Adapter contract for Fyers, Dhan, simulated, or future feeds."""

    def fetch_snapshot(self, instrument: str) -> MarketSnapshotPayload:
        """Return one normalized point-in-time market snapshot."""
