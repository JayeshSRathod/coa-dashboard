"""Governed CQRP rule-qualification domain models.

Rule qualification converts only successfully validated research patterns into
non-executable rule candidates. Qualified rules remain shadow-only until a later
governance decision explicitly authorizes assisted or controlled execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ALLOWED_STATUS = {
    "DRAFT",
    "QUALIFICATION_PENDING",
    "QUALIFIED",
    "CONDITIONAL",
    "REJECTED",
    "SUSPENDED",
    "RETIRED",
}
_ALLOWED_RECOMMENDATION = {
    "PROMOTE_TO_SHADOW_RULE",
    "QUALIFY_WITH_CONDITIONS",
    "COLLECT_MORE_EVIDENCE",
    "RETURN_TO_RESEARCH",
    "REJECT_RULE",
}
_ALLOWED_SCOPE = {"NEXT_SESSION", "INTRADAY"}


@dataclass(frozen=True)
class RuleDefinition:
    conditions: Mapping[str, Any]
    direction: str
    planning_horizons: tuple[str, ...]
    instruments: tuple[str, ...]
    scenarios: tuple[str, ...]
    regimes: tuple[str, ...]
    exclusions: Mapping[str, Any]
    risk_constraints: Mapping[str, Any]
    execution_constraints: Mapping[str, Any]

    @classmethod
    def new(cls, **values: Any) -> "RuleDefinition":
        values.setdefault("conditions", {})
        values.setdefault("direction", "POSITIVE")
        values.setdefault("planning_horizons", ())
        values.setdefault("instruments", ())
        values.setdefault("scenarios", ())
        values.setdefault("regimes", ())
        values.setdefault("exclusions", {})
        values.setdefault("risk_constraints", {})
        values.setdefault("execution_constraints", {"mode": "SHADOW_ONLY"})
        values["direction"] = str(values["direction"]).upper()
        values["planning_horizons"] = tuple(str(item).upper() for item in values["planning_horizons"])
        values["instruments"] = tuple(str(item) for item in values["instruments"])
        values["scenarios"] = tuple(str(item) for item in values["scenarios"])
        values["regimes"] = tuple(str(item) for item in values["regimes"])
        values["conditions"] = MappingProxyType(dict(values["conditions"]))
        values["exclusions"] = MappingProxyType(dict(values["exclusions"]))
        values["risk_constraints"] = MappingProxyType(dict(values["risk_constraints"]))
        values["execution_constraints"] = MappingProxyType(dict(values["execution_constraints"]))
        invalid = set(values["planning_horizons"]) - _ALLOWED_SCOPE
        if invalid:
            raise ValueError(f"unsupported planning horizons: {sorted(invalid)}")
        if not values["conditions"]:
            raise ValueError("rule conditions are required")
        if str(values["execution_constraints"].get("mode", "SHADOW_ONLY")).upper() != "SHADOW_ONLY":
            raise ValueError("Sprint-211 rules must remain SHADOW_ONLY")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "conditions": dict(self.conditions),
            "direction": self.direction,
            "planning_horizons": list(self.planning_horizons),
            "instruments": list(self.instruments),
            "scenarios": list(self.scenarios),
            "regimes": list(self.regimes),
            "exclusions": dict(self.exclusions),
            "risk_constraints": dict(self.risk_constraints),
            "execution_constraints": dict(self.execution_constraints),
        }


@dataclass(frozen=True)
class RuleQualificationResult:
    qualification_id: str
    rule_id: str
    pattern_id: str
    validation_id: str
    experiment_id: str | None
    status: str
    recommendation: str
    qualification_score: float
    definition: RuleDefinition
    validation_score: float
    confidence_score: float
    stability_score: float
    evidence_score: float
    governance_score: float
    sample_size: int
    validation_sample_size: int
    required_conditions: tuple[str, ...]
    failed_gates: tuple[str, ...]
    warnings: tuple[str, ...]
    lineage: Mapping[str, Any]
    rule_version: str
    created_at: str
    created_by: str = "RuleQualificationEngine"

    @classmethod
    def new(cls, **values: Any) -> "RuleQualificationResult":
        values.setdefault("qualification_id", str(uuid4()))
        values.setdefault("rule_id", str(uuid4()))
        values.setdefault("experiment_id", None)
        values.setdefault("status", "DRAFT")
        values.setdefault("recommendation", "COLLECT_MORE_EVIDENCE")
        values.setdefault("qualification_score", 0.0)
        values.setdefault("validation_score", 0.0)
        values.setdefault("confidence_score", 0.0)
        values.setdefault("stability_score", 0.0)
        values.setdefault("evidence_score", 0.0)
        values.setdefault("governance_score", 0.0)
        values.setdefault("sample_size", 0)
        values.setdefault("validation_sample_size", 0)
        values.setdefault("required_conditions", ())
        values.setdefault("failed_gates", ())
        values.setdefault("warnings", ())
        values.setdefault("lineage", {})
        values.setdefault("rule_version", "qualified-rule-v1")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "RuleQualificationEngine")

        values["status"] = str(values["status"]).upper()
        values["recommendation"] = str(values["recommendation"]).upper()
        for key in ("qualification_score", "validation_score", "confidence_score", "stability_score", "evidence_score", "governance_score"):
            values[key] = float(values[key])
        values["sample_size"] = int(values["sample_size"])
        values["validation_sample_size"] = int(values["validation_sample_size"])
        values["definition"] = values["definition"] if isinstance(values["definition"], RuleDefinition) else RuleDefinition.new(**values["definition"])
        values["required_conditions"] = tuple(str(item) for item in values["required_conditions"])
        values["failed_gates"] = tuple(str(item) for item in values["failed_gates"])
        values["warnings"] = tuple(str(item) for item in values["warnings"])
        values["lineage"] = MappingProxyType(dict(values["lineage"]))

        if values["status"] not in _ALLOWED_STATUS:
            raise ValueError("unsupported qualification status")
        if values["recommendation"] not in _ALLOWED_RECOMMENDATION:
            raise ValueError("unsupported qualification recommendation")
        for key in ("qualification_score", "validation_score", "confidence_score", "stability_score", "evidence_score", "governance_score"):
            if not 0.0 <= values[key] <= 100.0:
                raise ValueError(f"{key} must be between 0 and 100")
        if values["sample_size"] < 0 or values["validation_sample_size"] < 0:
            raise ValueError("sample sizes cannot be negative")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "qualification_id": self.qualification_id,
            "rule_id": self.rule_id,
            "pattern_id": self.pattern_id,
            "validation_id": self.validation_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "recommendation": self.recommendation,
            "qualification_score": round(self.qualification_score, 8),
            "definition": self.definition.as_dict(),
            "validation_score": round(self.validation_score, 8),
            "confidence_score": round(self.confidence_score, 8),
            "stability_score": round(self.stability_score, 8),
            "evidence_score": round(self.evidence_score, 8),
            "governance_score": round(self.governance_score, 8),
            "sample_size": self.sample_size,
            "validation_sample_size": self.validation_sample_size,
            "required_conditions": list(self.required_conditions),
            "failed_gates": list(self.failed_gates),
            "warnings": list(self.warnings),
            "lineage": dict(self.lineage),
            "rule_version": self.rule_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "mode": "SHADOW_RULE_ONLY",
        }
