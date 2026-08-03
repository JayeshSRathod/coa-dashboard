"""Read-only API facade for CQRP experiment validation artifacts."""

from __future__ import annotations

from src.experiment_validation.service import ExperimentValidationService


class ExperimentValidationApiV1:
    prefix = "/api/v1/experiment-validation"

    def __init__(self, service: ExperimentValidationService) -> None:
        self.service = service

    def get(self, validation_id: str) -> dict:
        record = self.service.get(validation_id)
        return {"status": 200 if record else 404, "data": record, "mode": "SHADOW_RESEARCH_ONLY"}

    def latest_for_pattern(self, pattern_id: str) -> dict:
        record = self.service.latest_for_pattern(pattern_id)
        return {"status": 200 if record else 404, "data": record, "mode": "SHADOW_RESEARCH_ONLY"}

    def list(
        self,
        *,
        status: str | None = None,
        pattern_id: str | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> dict:
        rows = self.service.list(
            status=status,
            pattern_id=pattern_id,
            experiment_id=experiment_id,
            limit=limit,
        )
        return {"status": 200, "data": rows, "count": len(rows), "mode": "SHADOW_RESEARCH_ONLY"}

    def passed(self, *, limit: int = 100) -> dict:
        return self.list(status="PASSED", limit=limit)

    def failed(self, *, limit: int = 100) -> dict:
        return self.list(status="FAILED", limit=limit)

    def inconclusive(self, *, limit: int = 100) -> dict:
        return self.list(status="INCONCLUSIVE", limit=limit)
