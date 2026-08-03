"""Immutable models for CQRP pre-market and intraday revalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class PreMarketObservation:
    trade_plan_id: str
    snapshot_id: str
    observed_at: str
    instrument: str
    planning_horizon: str
    previous_close: float
    observed_spot: float
    coa_bias: str
    technical_status: str | None
    technical_bias: str | None
    momentum_state: str | None
    risk_status: str
    data_quality: str
    news_risk: str = "NONE"
    global_score: float | None = None
    gift_nifty_change_pct: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trade_plan_id:
            raise ValueError("trade_plan_id is required")
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")
        if not self.instrument:
            raise ValueError("instrument is required")
        horizon = str(self.planning_horizon).upper()
        if horizon not in {"NEXT_SESSION", "INTRADAY"}:
            raise ValueError("planning_horizon must be NEXT_SESSION or INTRADAY")
        if self.previous_close <= 0 or self.observed_spot <= 0:
            raise ValueError("prices must be positive")
        object.__setattr__(self, "planning_horizon", horizon)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def gap_pct(self) -> float:
        return round(((self.observed_spot - self.previous_close) / self.previous_close) * 100.0, 4)


@dataclass(frozen=True)
class PreMarketValidationResult:
    validation_id: str
    trade_plan_id: str
    source_snapshot_id: str
    observed_snapshot_id: str
    planning_horizon: str
    validation_result: str
    selected_plan: str | None
    opening_classification: str
    confidence_before: float
    confidence_after: float
    risk_status: str
    data_quality: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence: Mapping[str, Any]
    validator_version: str
    created_at: str
    created_by: str = "PreMarketValidationEngine"

    @classmethod
    def new(cls, **values: Any) -> "PreMarketValidationResult":
        values.setdefault("validation_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "PreMarketValidationEngine")
        values["reasons"] = tuple(values.get("reasons", ()))
        values["warnings"] = tuple(values.get("warnings", ()))
        values["evidence"] = MappingProxyType(dict(values.get("evidence", {})))
        if values["validation_result"] not in {"VALIDATED", "MODIFIED", "CANCELLED", "OBSERVE_ONLY"}:
            raise ValueError("unsupported validation_result")
        if values.get("selected_plan") not in {None, "A", "B", "C"}:
            raise ValueError("selected_plan must be A, B, C, or None")
        if values["opening_classification"] not in {"GAP_UP", "GAP_DOWN", "FLAT"}:
            raise ValueError("unsupported opening_classification")
        for key in ("confidence_before", "confidence_after"):
            score = float(values[key])
            if not 0 <= score <= 100:
                raise ValueError(f"{key} must be between 0 and 100")
            values[key] = round(score, 4)
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "trade_plan_id": self.trade_plan_id,
            "source_snapshot_id": self.source_snapshot_id,
            "observed_snapshot_id": self.observed_snapshot_id,
            "planning_horizon": self.planning_horizon,
            "validation_result": self.validation_result,
            "selected_plan": self.selected_plan,
            "opening_classification": self.opening_classification,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "risk_status": self.risk_status,
            "data_quality": self.data_quality,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "evidence": dict(self.evidence),
            "validator_version": self.validator_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
