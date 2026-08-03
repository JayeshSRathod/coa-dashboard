"""Deterministic qualification of validated CQRP research patterns.

The engine accepts only passed experiment validations and emits shadow-rule
candidates. It cannot authorize broker execution or live trading.
"""

from __future__ import annotations

from typing import Any, Mapping

from src.experiment_validation.models import ValidationResult
from src.pattern_discovery.models import PatternCandidate

from .models import RuleDefinition, RuleQualificationResult


class RuleQualificationEngine:
    version = "rule-qualification-v1"

    def __init__(
        self,
        *,
        minimum_validation_score: float = 75.0,
        minimum_confidence_score: float = 60.0,
        minimum_stability_score: float = 60.0,
        minimum_combined_sample: int = 50,
        minimum_qualification_score: float = 75.0,
    ) -> None:
        self.minimum_validation_score = float(minimum_validation_score)
        self.minimum_confidence_score = float(minimum_confidence_score)
        self.minimum_stability_score = float(minimum_stability_score)
        self.minimum_combined_sample = int(minimum_combined_sample)
        self.minimum_qualification_score = float(minimum_qualification_score)

    def qualify(
        self,
        pattern: PatternCandidate | Mapping[str, Any],
        validation: ValidationResult | Mapping[str, Any],
        *,
        risk_constraints: Mapping[str, Any] | None = None,
        execution_constraints: Mapping[str, Any] | None = None,
    ) -> RuleQualificationResult:
        candidate = pattern if isinstance(pattern, PatternCandidate) else PatternCandidate.new(**dict(pattern))
        result = validation if isinstance(validation, ValidationResult) else ValidationResult.new(**dict(validation))

        if result.pattern_id != candidate.pattern_id:
            raise ValueError("validation does not belong to pattern")

        failed: list[str] = []
        warnings: list[str] = []
        if result.status != "PASSED":
            failed.append("VALIDATION_NOT_PASSED")
        if result.recommendation != "ELIGIBLE_FOR_RULE_QUALIFICATION":
            failed.append("VALIDATION_RECOMMENDATION_BLOCKS_QUALIFICATION")
        if result.validation_score < self.minimum_validation_score:
            failed.append("VALIDATION_SCORE_BELOW_MINIMUM")
        if candidate.confidence_score < self.minimum_confidence_score:
            failed.append("PATTERN_CONFIDENCE_BELOW_MINIMUM")
        if result.stability_score < self.minimum_stability_score:
            failed.append("VALIDATION_STABILITY_BELOW_MINIMUM")

        combined_sample = candidate.sample_size + result.validation_sample_size
        if combined_sample < self.minimum_combined_sample:
            failed.append("COMBINED_SAMPLE_BELOW_MINIMUM")

        evidence_score = min(100.0, combined_sample / max(1, self.minimum_combined_sample) * 100.0)
        governance_score = 100.0
        if candidate.warnings:
            governance_score -= min(30.0, len(candidate.warnings) * 10.0)
            warnings.extend(candidate.warnings)
        if result.warnings:
            governance_score -= min(30.0, len(result.warnings) * 10.0)
            warnings.extend(result.warnings)
        governance_score = max(0.0, governance_score)

        score = (
            result.validation_score * 0.35
            + candidate.confidence_score * 0.20
            + result.stability_score * 0.20
            + evidence_score * 0.15
            + governance_score * 0.10
        )
        score = round(max(0.0, min(100.0, score)), 8)

        if failed:
            if "VALIDATION_NOT_PASSED" in failed or "VALIDATION_RECOMMENDATION_BLOCKS_QUALIFICATION" in failed:
                status = "REJECTED"
                recommendation = "REJECT_RULE"
            elif score >= 60.0:
                status = "CONDITIONAL"
                recommendation = "COLLECT_MORE_EVIDENCE"
            else:
                status = "REJECTED"
                recommendation = "RETURN_TO_RESEARCH"
        elif score >= self.minimum_qualification_score:
            status = "QUALIFIED"
            recommendation = "PROMOTE_TO_SHADOW_RULE"
        else:
            status = "CONDITIONAL"
            recommendation = "QUALIFY_WITH_CONDITIONS"

        definition = RuleDefinition.new(
            conditions=dict(candidate.definition.feature_conditions),
            direction=candidate.direction,
            planning_horizons=candidate.definition.planning_horizons,
            instruments=candidate.definition.instruments,
            scenarios=candidate.definition.scenarios,
            regimes=candidate.definition.regimes,
            exclusions={},
            risk_constraints=dict(risk_constraints or {
                "max_position_risk_percent": 1.0,
                "max_concurrent_positions": 1,
                "paper_only": True,
            }),
            execution_constraints=dict(execution_constraints or {
                "mode": "SHADOW_ONLY",
                "assisted_execution_enabled": False,
                "live_order_enabled": False,
                "auto_trading_enabled": False,
            }),
        )

        required_conditions = tuple(
            item for item in (
                "CONTINUE_SHADOW_EVIDENCE_COLLECTION",
                "REVALIDATE_ON_DRIFT",
                "MANUAL_GOVERNANCE_APPROVAL_REQUIRED",
                "NO_LIVE_EXECUTION_AUTHORITY",
            )
        )

        return RuleQualificationResult.new(
            pattern_id=candidate.pattern_id,
            validation_id=result.validation_id,
            experiment_id=candidate.experiment_id,
            status=status,
            recommendation=recommendation,
            qualification_score=score,
            definition=definition,
            validation_score=result.validation_score,
            confidence_score=candidate.confidence_score,
            stability_score=result.stability_score,
            evidence_score=evidence_score,
            governance_score=governance_score,
            sample_size=candidate.sample_size,
            validation_sample_size=result.validation_sample_size,
            required_conditions=required_conditions,
            failed_gates=tuple(failed),
            warnings=tuple(dict.fromkeys(warnings)),
            lineage={
                "pattern_version": candidate.pattern_version,
                "validation_version": result.validation_version,
                "qualification_engine_version": self.version,
                "validation_recommendation": result.recommendation,
                "shadow_rule_only": True,
            },
        )
