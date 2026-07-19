"""Immutable CQRP research-signal model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ResearchSignal:
    signal_id: str
    snapshot_id: str
    coa_result_id: str
    validation_id: str
    session_id: str
    experiment_id: str | None
    strategy_version: str
    signal_version: str
    instrument: str
    expiry: str | None
    signal_type: str
    signal_state: str
    direction: str | None
    entry_price: float | None
    stop_loss: float | None
    target_1: float | None
    target_2: float | None
    trailing_reference: float | None
    confidence_score: float
    confidence_band: str
    scenario: str | None
    eos: float | None
    eor: float | None
    momentum: Mapping[str, Any] | None
    diversion: Mapping[str, Any] | None
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    created_at: str = field(default_factory=_utc_now)
    created_by: str = "SignalEngine"

    @classmethod
    def new(cls, **values: Any) -> "ResearchSignal":
        values.setdefault("signal_id", str(uuid4()))
        values.setdefault("created_at", _utc_now())
        if values["signal_type"] not in {"BUY", "SELL", "NO_SIGNAL", "WATCHLIST"}:
            raise ValueError("unsupported signal_type")
        if values["signal_state"] not in {"NEW", "ACTIVE", "EXPIRED", "CANCELLED"}:
            raise ValueError("unsupported signal_state")
        if values.get("direction") is not None and values["direction"] not in {"BUY", "SELL"}:
            raise ValueError("unsupported direction")
        confidence = float(values["confidence_score"])
        if not 0 <= confidence <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        values["confidence_score"] = round(confidence, 4)
        values["reasons"] = tuple(values.get("reasons", ()))
        values["warnings"] = tuple(values.get("warnings", ()))
        for name in ("momentum", "diversion", "details"):
            if values.get(name) is not None:
                values[name] = MappingProxyType(dict(values[name]))
        return cls(**values)

    def deterministic_values(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type, "signal_state": self.signal_state,
            "direction": self.direction, "entry_price": self.entry_price,
            "stop_loss": self.stop_loss, "target_1": self.target_1, "target_2": self.target_2,
            "trailing_reference": self.trailing_reference, "confidence_score": self.confidence_score,
            "confidence_band": self.confidence_band, "scenario": self.scenario, "eos": self.eos,
            "eor": self.eor, "momentum": dict(self.momentum) if self.momentum else None,
            "diversion": dict(self.diversion) if self.diversion else None,
            "reasons": self.reasons, "warnings": self.warnings, "details": dict(self.details),
        }
