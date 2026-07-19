"""Immutable models for CQRP validation evidence and confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ComponentAssessment:
    name: str
    score: float
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, **values: Any) -> "ComponentAssessment":
        score = float(values["score"])
        if not 0 <= score <= 100:
            raise ValueError("component score must be between 0 and 100")
        values["score"] = round(score, 4)
        values["reasons"] = tuple(values.get("reasons", ()))
        values["warnings"] = tuple(values.get("warnings", ()))
        values["failures"] = tuple(values.get("failures", ()))
        values["details"] = MappingProxyType(dict(values.get("details", {})))
        return cls(**values)


@dataclass(frozen=True)
class ValidationResult:
    validation_id: str
    coa_result_id: str
    snapshot_id: str
    session_id: str
    experiment_id: str | None
    strategy_version: str
    validation_version: str
    volume_score: float
    oi_score: float
    strike_score: float
    liquidity_score: float
    market_context_score: float
    historical_score: float | None
    overall_score: float
    confidence_band: str
    is_valid: bool
    failure_reasons: tuple[str, ...] = ()
    warning_reasons: tuple[str, ...] = ()
    scoring_details: Mapping[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    created_at: str = field(default_factory=_utc_now)
    created_by: str = "ValidationEngine"

    @classmethod
    def new(cls, **values: Any) -> "ValidationResult":
        values.setdefault("validation_id", str(uuid4()))
        values.setdefault("created_at", _utc_now())
        for name in ("volume_score", "oi_score", "strike_score", "liquidity_score",
                     "market_context_score", "overall_score"):
            score = float(values[name])
            if not 0 <= score <= 100:
                raise ValueError(name + " must be between 0 and 100")
            values[name] = round(score, 4)
        if values.get("historical_score") is not None:
            values["historical_score"] = round(float(values["historical_score"]), 4)
        values["failure_reasons"] = tuple(values.get("failure_reasons", ()))
        values["warning_reasons"] = tuple(values.get("warning_reasons", ()))
        values["scoring_details"] = MappingProxyType(dict(values.get("scoring_details", {})))
        return cls(**values)
