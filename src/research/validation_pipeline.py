"""Application pipeline for deterministic validation of persisted COA research."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from src.persistence.coa_result_repository import COAResultRepository
from src.persistence.snapshot_repository import SnapshotRepository
from src.persistence.validation_repository import ValidationRepository
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult

from .observability import emit_snapshot_event


@dataclass(frozen=True)
class ValidationProcessingOutcome:
    coa_result_id: str
    success: bool
    result: ValidationResult | None = None
    error: str | None = None


class ValidationResearchPipeline:
    """Loads linked evidence, evaluates it, and appends the resulting record."""

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        coa_result_repository: COAResultRepository,
        validation_repository: ValidationRepository,
        validation_engine: ValidationEngine,
        logger: logging.Logger | None = None,
    ) -> None:
        self.snapshot_repository = snapshot_repository
        self.coa_result_repository = coa_result_repository
        self.validation_repository = validation_repository
        self.validation_engine = validation_engine
        self.logger = logger or logging.getLogger("cqrp.validation_pipeline")

    def process_coa_result_id(
        self, coa_result_id: str, *, experiment_id: str | None = None
    ) -> ValidationProcessingOutcome:
        coa_result = self.coa_result_repository.get(coa_result_id)
        if coa_result is None:
            return ValidationProcessingOutcome(coa_result_id, False, error="COA result not found")
        snapshot = self.snapshot_repository.get(coa_result.snapshot_id)
        if snapshot is None:
            return ValidationProcessingOutcome(coa_result_id, False, error="linked snapshot not found")
        emit_snapshot_event(
            self.logger, "validation_started", coa_result_id=coa_result_id,
            snapshot_id=coa_result.snapshot_id, session_id=coa_result.session_id,
            experiment_id=experiment_id, validation_version=self.validation_engine.validation_version,
        )
        try:
            result = self.validation_engine.evaluate(
                snapshot, coa_result, experiment_id=experiment_id
            )
            stored = self.validation_repository.append(result)
        except Exception as exc:
            self.snapshot_repository.record_event(
                "validation_failed", "ERROR",
                {"coa_result_id": coa_result_id, "snapshot_id": coa_result.snapshot_id,
                 "session_id": coa_result.session_id, "experiment_id": experiment_id,
                 "validation_version": self.validation_engine.validation_version, "error": str(exc)},
                snapshot.get("instrument"),
            )
            emit_snapshot_event(
                self.logger, "validation_failed", coa_result_id=coa_result_id,
                snapshot_id=coa_result.snapshot_id, error=str(exc),
            )
            return ValidationProcessingOutcome(coa_result_id, False, error=str(exc))
        emit_snapshot_event(
            self.logger, "validation_completed", coa_result_id=coa_result_id,
            snapshot_id=stored.snapshot_id, session_id=stored.session_id,
            validation_id=stored.validation_id, overall_score=stored.overall_score,
            confidence_band=stored.confidence_band, is_valid=stored.is_valid,
        )
        return ValidationProcessingOutcome(coa_result_id, True, result=stored)

    def process_session(
        self, session_id: str, *, experiment_id: str | None = None
    ) -> list[ValidationProcessingOutcome]:
        return [
            self.process_coa_result_id(result.coa_result_id, experiment_id=experiment_id)
            for result in self.coa_result_repository.list_by_session(session_id)
        ]
