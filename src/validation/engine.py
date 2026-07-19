"""Configuration-driven deterministic validation orchestrator."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter

from src.coa.models import COAResearchResult

from .config import ValidationConfig
from .liquidity import LiquidityValidator
from .market_context import MarketContextValidator
from .models import ComponentAssessment, ValidationResult
from .open_interest import OpenInterestValidator
from .scoring import confidence_band, weighted_score
from .strike_quality import StrikeQualityValidator
from .volume import VolumeValidator


class ValidationEngine:
    """Aggregates evidence components; it does not create a trade signal."""

    created_by = "ValidationEngine"

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig()
        self.components = (
            VolumeValidator(),
            OpenInterestValidator(),
            StrikeQualityValidator(),
            LiquidityValidator(),
            MarketContextValidator(self.config),
        )

    @property
    def validation_version(self) -> str:
        return self.config.validation_version

    def evaluate(
        self,
        snapshot: Mapping[str, object],
        coa_result: COAResearchResult,
        *,
        experiment_id: str | None = None,
    ) -> ValidationResult:
        started = perf_counter()
        assessments: dict[str, ComponentAssessment] = {
            component.name: component.assess(snapshot, coa_result) for component in self.components
        }
        scores = {name: assessment.score for name, assessment in assessments.items()}
        overall = weighted_score(scores, self.config.weights)
        failures = tuple(
            reason for assessment in assessments.values() for reason in assessment.failures
        )
        warnings = tuple(
            reason for assessment in assessments.values() for reason in assessment.warnings
        )
        details = {
            "weights": dict(self.config.weights),
            "components": {
                name: {
                    "score": assessment.score, "reasons": assessment.reasons,
                    "warnings": assessment.warnings, "failures": assessment.failures,
                    "details": dict(assessment.details),
                } for name, assessment in assessments.items()
            },
            "historical_evidence": {"status": "not_available_in_sprint_005"},
        }
        return ValidationResult.new(
            coa_result_id=coa_result.coa_result_id,
            snapshot_id=coa_result.snapshot_id,
            session_id=coa_result.session_id,
            experiment_id=experiment_id,
            strategy_version=coa_result.strategy_version,
            validation_version=self.validation_version,
            volume_score=scores["volume"],
            oi_score=scores["open_interest"],
            strike_score=scores["strike_quality"],
            liquidity_score=scores["liquidity"],
            market_context_score=scores["market_context"],
            historical_score=None,
            overall_score=overall,
            confidence_band=confidence_band(overall),
            is_valid=not failures and overall >= self.config.minimum_valid_score,
            failure_reasons=failures,
            warning_reasons=warnings,
            scoring_details=details,
            processing_time_ms=(perf_counter() - started) * 1000,
            created_by=self.created_by,
        )
