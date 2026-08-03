"""Immutable models for deterministic next-session PAPER trade plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TradePlanningInput:
    snapshot_id: str
    signal_id: str | None
    risk_decision_id: str | None
    instrument: str
    expiry: str | None
    spot: float
    scenario_number: int | None
    scenario: str | None
    risk_mode: str | None
    support: float | None
    resistance: float | None
    eos: float | None
    eor: float | None
    direction: str | None
    signal_type: str | None
    entry: float | None
    stop_loss: float | None
    target_1: float | None
    target_2: float | None
    confidence_score: float
    validation_passed: bool
    technical_status: str | None = None
    technical_bias: str | None = None
    momentum_state: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")
        if not self.instrument:
            raise ValueError("instrument is required")
        if self.direction not in {None, "BUY", "SELL"}:
            raise ValueError("direction must be BUY, SELL, or None")
        confidence = float(self.confidence_score)
        if not 0 <= confidence <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        object.__setattr__(self, "confidence_score", round(confidence, 4))
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))


@dataclass(frozen=True)
class OpeningPlan:
    code: str
    opening_condition: str
    action: str
    entry_condition: str
    invalidation: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.code not in {"A", "B", "C"}:
            raise ValueError("opening plan code must be A, B, or C")
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True)
class TradePlan:
    trade_plan_id: str
    snapshot_id: str
    signal_id: str | None
    risk_decision_id: str | None
    instrument: str
    expiry: str | None
    planning_horizon: str
    market_bias: str
    expected_opening: str
    direction: str | None
    option_type: str | None
    entry: float | None
    stop_loss: float | None
    target_1: float | None
    target_2: float | None
    confidence_score: float
    readiness: str
    status: str
    valid_for_session: str | None
    rationale: tuple[str, ...]
    warnings: tuple[str, ...]
    opening_plans: tuple[OpeningPlan, ...]
    evidence: Mapping[str, Any]
    planner_version: str
    created_at: str
    created_by: str = "TradePlanningEngine"

    @classmethod
    def new(cls, **values: Any) -> "TradePlan":
        values.setdefault("trade_plan_id", str(uuid4()))
        values.setdefault("planning_horizon", "NEXT_SESSION")
        values.setdefault("planner_version", "trade-planner-v1")
        values.setdefault("created_at", _utc_now())
        values.setdefault("created_by", "TradePlanningEngine")
        values["rationale"] = tuple(values.get("rationale", ()))
        values["warnings"] = tuple(values.get("warnings", ()))
        values["opening_plans"] = tuple(values.get("opening_plans", ()))
        values["evidence"] = MappingProxyType(dict(values.get("evidence", {})))
        if values.get("direction") not in {None, "BUY", "SELL"}:
            raise ValueError("unsupported direction")
        if values.get("option_type") not in {None, "CE", "PE"}:
            raise ValueError("unsupported option_type")
        if values.get("market_bias") not in {"BULLISH", "BEARISH", "NEUTRAL", "UNCERTAIN"}:
            raise ValueError("unsupported market_bias")
        if values.get("expected_opening") not in {"GAP_UP", "GAP_DOWN", "FLAT", "UNCERTAIN"}:
            raise ValueError("unsupported expected_opening")
        if values.get("readiness") not in {"READY", "CONDITIONAL", "OBSERVE_ONLY", "BLOCKED"}:
            raise ValueError("unsupported readiness")
        if values.get("status") not in {"PRELIMINARY", "PREOPEN_CONFIRMED", "CANCELLED", "EXPIRED"}:
            raise ValueError("unsupported status")
        confidence = float(values["confidence_score"])
        if not 0 <= confidence <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        values["confidence_score"] = round(confidence, 4)
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trade_plan_id": self.trade_plan_id,
            "snapshot_id": self.snapshot_id,
            "signal_id": self.signal_id,
            "risk_decision_id": self.risk_decision_id,
            "instrument": self.instrument,
            "expiry": self.expiry,
            "planning_horizon": self.planning_horizon,
            "market_bias": self.market_bias,
            "expected_opening": self.expected_opening,
            "direction": self.direction,
            "option_type": self.option_type,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "confidence_score": self.confidence_score,
            "readiness": self.readiness,
            "status": self.status,
            "valid_for_session": self.valid_for_session,
            "rationale": list(self.rationale),
            "warnings": list(self.warnings),
            "opening_plans": [
                {
                    "code": item.code,
                    "opening_condition": item.opening_condition,
                    "action": item.action,
                    "entry_condition": item.entry_condition,
                    "invalidation": item.invalidation,
                    "notes": list(item.notes),
                }
                for item in self.opening_plans
            ],
            "evidence": dict(self.evidence),
            "planner_version": self.planner_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
