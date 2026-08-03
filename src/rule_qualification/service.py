"""Application service for governed CQRP shadow rule qualification."""

from __future__ import annotations

from typing import Any, Mapping

from src.experiment_validation.models import ValidationResult
from src.pattern_discovery.models import PatternCandidate
from src.persistence.rule_qualification_repository import RuleQualificationRepository

from .engine import RuleQualificationEngine
from .models import RuleQualificationResult


class RuleQualificationService:
    def __init__(
        self,
        repository: RuleQualificationRepository,
        engine: RuleQualificationEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or RuleQualificationEngine()

    def qualify(
        self,
        pattern: PatternCandidate | Mapping[str, Any],
        validation: ValidationResult | Mapping[str, Any],
    ) -> dict[str, Any]:
        result = self.engine.qualify(pattern, validation)
        self.repository.append(result)
        return result.as_dict()

    def get(self, qualification_id: str) -> dict[str, Any] | None:
        return self.repository.get(qualification_id)

    def latest_for_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        return self.repository.latest_for_pattern(pattern_id)

    def list(
        self,
        *,
        status: str | None = None,
        recommendation: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.repository.list(status=status, recommendation=recommendation, limit=limit)

    @staticmethod
    def rehydrate(record: Mapping[str, Any]) -> RuleQualificationResult:
        return RuleQualificationResult.new(**dict(record))
