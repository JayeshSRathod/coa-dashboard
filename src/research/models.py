"""Internal immutable snapshot model used by capture and replay services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class CapturedSnapshot:
    snapshot_id: str
    session_id: str
    instrument: str
    spot: float
    source: str
    market_captured_at: str
    ingested_at: str
    option_chain: list[dict[str, Any]]
    futures_price: float | None = None
    atm_strike: float | None = None
    expiry: str | None = None
    expiry_type: str | None = None
    source_latency_ms: int | None = None
    coa_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, **values: Any) -> "CapturedSnapshot":
        return cls(snapshot_id=values.pop("snapshot_id", str(uuid4())), **values)
