"""Application service for CQRP research-only experiment validation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.persistence.experiment_validation_repository import ExperimentValidationRepository

from .engine import ExperimentValidationEngine
from .models import ValidationResult


class ExperimentValidationService:
    def __init__(
        self,
        repository: ExperimentValidationRepository,
        engine: ExperimentValidationEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or ExperimentValidationEngine()

    def validate(
        self,
        pattern: Mapping[str, Any],
        evidence_records: Iterable[Mapping[str, Any]],
    ) -> ValidationResult:
        result = self.engine.validate(pattern, evidence_records)
        self.repository.append(result)
        return result

    def get(self, validation_id: str) -> dict[str, Any] | None:
        return self.repository.get(validation_id)

    def latest_for_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        return self.repository.latest_for_pattern(pattern_id)

    def list(
        self,
        *,
        status: str | None = None,
        pattern_id: str | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.repository.list(
            status=status,
            pattern_id=pattern_id,
            experiment_id=experiment_id,
            limit=limit,
        )
