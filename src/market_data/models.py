"""Immutable, provider-neutral market-data models for CQRP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QualityState(StrEnum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    STALE = "STALE"
    OFFLINE = "OFFLINE"
    INCOMPLETE = "INCOMPLETE"
    WARMING = "WARMING"
    RECOVERING = "RECOVERING"


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True)
class MarketQuote:
    instrument_id: str
    provider: str
    ltp: float
    timestamp: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    age_seconds: float | None = None
    quality: QualityState = QualityState.WARMING


@dataclass(frozen=True)
class Candle:
    instrument_id: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    oi: float | None = None
    vwap: float | None = None


@dataclass(frozen=True)
class OptionContract:
    instrument_id: str
    strike: float
    expiry: str
    option_type: str
    premium: float
    provider: str
    timestamp: str
    volume: float | None = None
    oi: float | None = None
    oi_change: float | None = None
    iv: float | None = None
    greeks: dict[str, float] = field(default_factory=dict)
    bid: float | None = None
    ask: float | None = None
    bid_quantity: float | None = None
    ask_quantity: float | None = None

    @property
    def spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid


@dataclass(frozen=True)
class OptionChainSnapshot:
    snapshot_id: str
    instrument_id: str
    spot: float
    expiry: str
    provider: str
    captured_at: str
    contracts: tuple[OptionContract, ...]
    futures_price: float | None = None
    latency_ms: float | None = None
    quality: QualityState = QualityState.WARMING
    quality_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, **values: Any) -> "OptionChainSnapshot":
        values.setdefault("snapshot_id", str(uuid4()))
        values.setdefault("captured_at", utc_now())
        values["contracts"] = tuple(values.get("contracts", ()))
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["quality"] = self.quality.value
        return data

    def coa_rows(self) -> list[dict[str, Any]]:
        """Return the legacy COA column shape without exposing broker JSON."""
        strikes: dict[float, dict[str, float]] = {}
        for contract in self.contracts:
            row = strikes.setdefault(contract.strike, {
                "Strike": contract.strike, "Call_OI": 0.0, "Call_Vol": 0.0,
                "Call_LTP": 0.0, "Put_LTP": 0.0, "Put_Vol": 0.0, "Put_OI": 0.0,
                "Call_Bid": None, "Call_Ask": None, "Call_OI_Change": None, "Call_IV": None,
                "Call_Delta": None, "Call_Gamma": None, "Call_Theta": None, "Call_Vega": None,
                "Call_Bid_Qty": None, "Call_Ask_Qty": None,
                "Put_Bid": None, "Put_Ask": None, "Put_OI_Change": None, "Put_IV": None,
                "Put_Delta": None, "Put_Gamma": None, "Put_Theta": None, "Put_Vega": None,
                "Put_Bid_Qty": None, "Put_Ask_Qty": None,
            })
            if contract.option_type == "CE":
                row.update({
                    "Call_OI": float(contract.oi or 0), "Call_Vol": float(contract.volume or 0),
                    "Call_LTP": contract.premium, "Call_Bid": contract.bid, "Call_Ask": contract.ask,
                    "Call_OI_Change": contract.oi_change, "Call_IV": contract.iv,
                    "Call_Delta": contract.greeks.get("delta"), "Call_Gamma": contract.greeks.get("gamma"),
                    "Call_Theta": contract.greeks.get("theta"), "Call_Vega": contract.greeks.get("vega"),
                    "Call_Bid_Qty": contract.bid_quantity, "Call_Ask_Qty": contract.ask_quantity,
                })
            elif contract.option_type == "PE":
                row.update({
                    "Put_OI": float(contract.oi or 0), "Put_Vol": float(contract.volume or 0),
                    "Put_LTP": contract.premium, "Put_Bid": contract.bid, "Put_Ask": contract.ask,
                    "Put_OI_Change": contract.oi_change, "Put_IV": contract.iv,
                    "Put_Delta": contract.greeks.get("delta"), "Put_Gamma": contract.greeks.get("gamma"),
                    "Put_Theta": contract.greeks.get("theta"), "Put_Vega": contract.greeks.get("vega"),
                    "Put_Bid_Qty": contract.bid_quantity, "Put_Ask_Qty": contract.ask_quantity,
                })
        return [strikes[strike] for strike in sorted(strikes)]


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    observed_at: str
    availability: QualityState
    latency_ms: float | None
    error_count: int
    heartbeat_at: str | None
    circuit_state: CircuitState = CircuitState.CLOSED
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceTransition:
    transition_id: str
    instrument_id: str
    from_provider: str | None
    to_provider: str
    reason: str
    occurred_at: str

    @classmethod
    def new(cls, **values: Any) -> "SourceTransition":
        values.setdefault("transition_id", str(uuid4()))
        values.setdefault("occurred_at", utc_now())
        return cls(**values)
