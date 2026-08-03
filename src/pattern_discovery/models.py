"""Immutable CQRP pattern-discovery domain models.

Pattern discovery operates only on persisted evidence, statistics snapshots, and
research experiments. Discovered patterns are research candidates, never trading
rules, until they pass experiment validation and rule qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ALLOWED_STATUS = {"DISCOVERED", "REVIEW_PENDING", "VALIDATION_PENDING", "REJECTED", "PROMOTED", "ARCHIVED"}
_ALLOWED_DIRECTION = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
_ALLOWED_METHOD = {"GROUP_COMPARISON", "THRESHOLD_SCAN", "FEATURE_INTERACTION", "SEQUENCE", "REGIME_SEGMENTATION"}


@dataclass(frozen=True)
class PatternDefinition:
    feature_conditions: Mapping[str, Any]
    outcome_target: str
    comparison_group: Mapping[str, Any]
    planning_horizons: tuple[str, ...]
    instruments: tuple[str, ...]
    scenarios: tuple[str, ...]
    regimes: tuple[str, ...]

    @classmethod
    def new(cls, **values: Any) -> "PatternDefinition":
        values.setdefault("feature_conditions", {})
        values.setdefault("comparison_group", {})
        values.setdefault("planning_horizons", ())
        values.setdefault("instruments", ())
        values.setdefault("scenarios", ())
        values.setdefault("regimes", ())
        values["feature_conditions"] = MappingProxyType(dict(values["feature_conditions"]))
        values["comparison_group"] = MappingProxyType(dict(values["comparison_group"]))
        values["planning_horizons"] = tuple(str(item).upper() for item in values["planning_horizons"])
        values["instruments"] = tuple(str(item) for item in values["instruments"])
        values["scenarios"] = tuple(str(item) for item in values["scenarios"])
        values["regimes"] = tuple(str(item) for item in values["regimes"])
        if not str(values.get("outcome_target") or "").strip():
            raise ValueError("outcome_target is required")
        invalid_horizons = set(values["planning_horizons"]) - {"NEXT_SESSION", "INTRADAY"}
        if invalid_horizons:
            raise ValueError(f"unsupported planning horizons: {sorted(invalid_horizons)}")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_conditions": dict(self.feature_conditions),
            "outcome_target": self.outcome_target,
            "comparison_group": dict(self.comparison_group),
            "planning_horizons": list(self.planning_horizons),
            "instruments": list(self.instruments),
            "scenarios": list(self.scenarios),
            "regimes": list(self.regimes),
        }


@dataclass(frozen=True)
class PatternCandidate:
    pattern_id: str
    experiment_id: str | None
    source_run_id: str | None
    statistics_snapshot_id: str | None
    title: str
    description: str
    status: str
    discovery_method: str
    direction: str
    definition: PatternDefinition
    sample_size: int
    comparison_sample_size: int
    support_rate: float
    baseline_rate: float | None
    uplift: float | None
    average_r_multiple: float | None
    expectancy_r: float | None
    confidence_score: float
    stability_score: float
    evidence_ids: tuple[str, ...]
    supporting_metrics: Mapping[str, Any]
    warnings: tuple[str, ...]
    pattern_version: str
    created_at: str
    created_by: str = "PatternDiscoveryEngine"

    @classmethod
    def new(cls, **values: Any) -> "PatternCandidate":
        values.setdefault("pattern_id", str(uuid4()))
        values.setdefault("experiment_id", None)
        values.setdefault("source_run_id", None)
        values.setdefault("statistics_snapshot_id", None)
        values.setdefault("status", "DISCOVERED")
        values.setdefault("discovery_method", "GROUP_COMPARISON")
        values.setdefault("direction", "POSITIVE")
        values.setdefault("sample_size", 0)
        values.setdefault("comparison_sample_size", 0)
        values.setdefault("support_rate", 0.0)
        values.setdefault("baseline_rate", None)
        values.setdefault("uplift", None)
        values.setdefault("average_r_multiple", None)
        values.setdefault("expectancy_r", None)
        values.setdefault("confidence_score", 0.0)
        values.setdefault("stability_score", 0.0)
        values.setdefault("evidence_ids", ())
        values.setdefault("supporting_metrics", {})
        values.setdefault("warnings", ())
        values.setdefault("pattern_version", "pattern-candidate-v1")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "PatternDiscoveryEngine")

        values["status"] = str(values["status"]).upper()
        values["discovery_method"] = str(values["discovery_method"]).upper()
        values["direction"] = str(values["direction"]).upper()
        values["definition"] = (
            values["definition"]
            if isinstance(values["definition"], PatternDefinition)
            else PatternDefinition.new(**values["definition"])
        )
        values["sample_size"] = int(values["sample_size"])
        values["comparison_sample_size"] = int(values["comparison_sample_size"])
        values["support_rate"] = float(values["support_rate"])
        values["confidence_score"] = float(values["confidence_score"])
        values["stability_score"] = float(values["stability_score"])
        values["evidence_ids"] = tuple(str(item) for item in values["evidence_ids"])
        values["supporting_metrics"] = MappingProxyType(dict(values["supporting_metrics"]))
        values["warnings"] = tuple(str(item) for item in values["warnings"])

        if not str(values.get("title") or "").strip():
            raise ValueError("title is required")
        if not str(values.get("description") or "").strip():
            raise ValueError("description is required")
        if values["status"] not in _ALLOWED_STATUS:
            raise ValueError("unsupported pattern status")
        if values["direction"] not in _ALLOWED_DIRECTION:
            raise ValueError("unsupported pattern direction")
        if values["discovery_method"] not in _ALLOWED_METHOD:
            raise ValueError("unsupported discovery method")
        if values["sample_size"] < 1:
            raise ValueError("sample_size must be positive")
        if values["comparison_sample_size"] < 0:
            raise ValueError("comparison_sample_size cannot be negative")
        if not 0.0 <= values["support_rate"] <= 100.0:
            raise ValueError("support_rate must be between 0 and 100")
        if not 0.0 <= values["confidence_score"] <= 100.0:
            raise ValueError("confidence_score must be between 0 and 100")
        if not 0.0 <= values["stability_score"] <= 100.0:
            raise ValueError("stability_score must be between 0 and 100")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "experiment_id": self.experiment_id,
            "source_run_id": self.source_run_id,
            "statistics_snapshot_id": self.statistics_snapshot_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "discovery_method": self.discovery_method,
            "direction": self.direction,
            "definition": self.definition.as_dict(),
            "sample_size": self.sample_size,
            "comparison_sample_size": self.comparison_sample_size,
            "support_rate": round(self.support_rate, 8),
            "baseline_rate": self.baseline_rate,
            "uplift": self.uplift,
            "average_r_multiple": self.average_r_multiple,
            "expectancy_r": self.expectancy_r,
            "confidence_score": round(self.confidence_score, 8),
            "stability_score": round(self.stability_score, 8),
            "evidence_ids": list(self.evidence_ids),
            "supporting_metrics": dict(self.supporting_metrics),
            "warnings": list(self.warnings),
            "pattern_version": self.pattern_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
