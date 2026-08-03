"""Immutable domain models for CQRP experiment and pattern validation.

Validation artifacts are research-only. They evaluate discovered patterns on
unseen evidence and cannot produce broker instructions or executable rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ALLOWED_STATUS = {"QUEUED", "RUNNING", "PASSED", "FAILED", "INCONCLUSIVE"}
_ALLOWED_RECOMMENDATION = {
    "ELIGIBLE_FOR_RULE_QUALIFICATION",
    "COLLECT_MORE_EVIDENCE",
    "RETURN_TO_RESEARCH",
    "REJECT_PATTERN",
}


@dataclass(frozen=True)
class ValidationMetric:
    name: str
    value: float | None
    threshold: float | None
    passed: bool | None
    weight: float
    details: Mapping[str, Any]

    @classmethod
    def new(cls, **values: Any) -> "ValidationMetric":
        values.setdefault("value", None)
        values.setdefault("threshold", None)
        values.setdefault("passed", None)
        values.setdefault("weight", 1.0)
        values.setdefault("details", {})
        values["name"] = str(values["name"])
        values["weight"] = float(values["weight"])
        values["details"] = MappingProxyType(dict(values["details"]))
        if not values["name"].strip():
            raise ValueError("metric name is required")
        if values["weight"] < 0:
            raise ValueError("metric weight cannot be negative")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "weight": self.weight,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ValidationResult:
    validation_id: str
    pattern_id: str
    experiment_id: str | None
    status: str
    recommendation: str
    validation_score: float
    discovery_sample_size: int
    validation_sample_size: int
    in_sample_win_rate: float | None
    out_of_sample_win_rate: float | None
    in_sample_expectancy_r: float | None
    out_of_sample_expectancy_r: float | None
    degradation_percent: float | None
    stability_score: float
    walk_forward_score: float
    bootstrap_score: float
    monte_carlo_score: float
    drift_score: float
    sensitivity_score: float
    metrics: tuple[ValidationMetric, ...]
    evidence_ids: tuple[str, ...]
    discovery_evidence_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    lineage: Mapping[str, Any]
    validation_version: str
    created_at: str
    created_by: str = "ExperimentValidationEngine"

    @classmethod
    def new(cls, **values: Any) -> "ValidationResult":
        values.setdefault("validation_id", str(uuid4()))
        values.setdefault("experiment_id", None)
        values.setdefault("status", "QUEUED")
        values.setdefault("recommendation", "COLLECT_MORE_EVIDENCE")
        values.setdefault("validation_score", 0.0)
        values.setdefault("discovery_sample_size", 0)
        values.setdefault("validation_sample_size", 0)
        values.setdefault("in_sample_win_rate", None)
        values.setdefault("out_of_sample_win_rate", None)
        values.setdefault("in_sample_expectancy_r", None)
        values.setdefault("out_of_sample_expectancy_r", None)
        values.setdefault("degradation_percent", None)
        values.setdefault("stability_score", 0.0)
        values.setdefault("walk_forward_score", 0.0)
        values.setdefault("bootstrap_score", 0.0)
        values.setdefault("monte_carlo_score", 0.0)
        values.setdefault("drift_score", 0.0)
        values.setdefault("sensitivity_score", 0.0)
        values.setdefault("metrics", ())
        values.setdefault("evidence_ids", ())
        values.setdefault("discovery_evidence_ids", ())
        values.setdefault("warnings", ())
        values.setdefault("lineage", {})
        values.setdefault("validation_version", "experiment-validation-v1")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "ExperimentValidationEngine")

        values["status"] = str(values["status"]).upper()
        values["recommendation"] = str(values["recommendation"]).upper()
        values["validation_score"] = float(values["validation_score"])
        values["discovery_sample_size"] = int(values["discovery_sample_size"])
        values["validation_sample_size"] = int(values["validation_sample_size"])
        values["stability_score"] = float(values["stability_score"])
        values["walk_forward_score"] = float(values["walk_forward_score"])
        values["bootstrap_score"] = float(values["bootstrap_score"])
        values["monte_carlo_score"] = float(values["monte_carlo_score"])
        values["drift_score"] = float(values["drift_score"])
        values["sensitivity_score"] = float(values["sensitivity_score"])
        values["metrics"] = tuple(
            item if isinstance(item, ValidationMetric) else ValidationMetric.new(**item)
            for item in values["metrics"]
        )
        values["evidence_ids"] = tuple(str(item) for item in values["evidence_ids"])
        values["discovery_evidence_ids"] = tuple(str(item) for item in values["discovery_evidence_ids"])
        values["warnings"] = tuple(str(item) for item in values["warnings"])
        values["lineage"] = MappingProxyType(dict(values["lineage"]))

        if values["status"] not in _ALLOWED_STATUS:
            raise ValueError("unsupported validation status")
        if values["recommendation"] not in _ALLOWED_RECOMMENDATION:
            raise ValueError("unsupported validation recommendation")
        if not 0.0 <= values["validation_score"] <= 100.0:
            raise ValueError("validation_score must be between 0 and 100")
        if values["discovery_sample_size"] < 0 or values["validation_sample_size"] < 0:
            raise ValueError("sample sizes cannot be negative")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "pattern_id": self.pattern_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "recommendation": self.recommendation,
            "validation_score": round(self.validation_score, 8),
            "discovery_sample_size": self.discovery_sample_size,
            "validation_sample_size": self.validation_sample_size,
            "in_sample_win_rate": self.in_sample_win_rate,
            "out_of_sample_win_rate": self.out_of_sample_win_rate,
            "in_sample_expectancy_r": self.in_sample_expectancy_r,
            "out_of_sample_expectancy_r": self.out_of_sample_expectancy_r,
            "degradation_percent": self.degradation_percent,
            "stability_score": round(self.stability_score, 8),
            "walk_forward_score": round(self.walk_forward_score, 8),
            "bootstrap_score": round(self.bootstrap_score, 8),
            "monte_carlo_score": round(self.monte_carlo_score, 8),
            "drift_score": round(self.drift_score, 8),
            "sensitivity_score": round(self.sensitivity_score, 8),
            "metrics": [item.as_dict() for item in self.metrics],
            "evidence_ids": list(self.evidence_ids),
            "discovery_evidence_ids": list(self.discovery_evidence_ids),
            "warnings": list(self.warnings),
            "lineage": dict(self.lineage),
            "validation_version": self.validation_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
