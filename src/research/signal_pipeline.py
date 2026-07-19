"""Research-only pipeline for deterministic signal recommendation generation."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from src.persistence.coa_result_repository import COAResultRepository
from src.persistence.signal_repository import SignalRepository
from src.persistence.snapshot_repository import SnapshotRepository
from src.persistence.validation_repository import ValidationRepository
from src.signal.engine import SignalEngine
from src.signal.models import ResearchSignal

from .observability import emit_snapshot_event


@dataclass(frozen=True)
class SignalProcessingOutcome:
    validation_id: str
    success: bool
    signal: ResearchSignal | None = None
    error: str | None = None


class SignalResearchPipeline:
    """Turns validated research into persisted recommendations, never orders."""

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        coa_result_repository: COAResultRepository,
        validation_repository: ValidationRepository,
        signal_repository: SignalRepository,
        signal_engine: SignalEngine,
        logger: logging.Logger | None = None,
    ) -> None:
        self.snapshot_repository = snapshot_repository
        self.coa_result_repository = coa_result_repository
        self.validation_repository = validation_repository
        self.signal_repository = signal_repository
        self.signal_engine = signal_engine
        self.logger = logger or logging.getLogger("cqrp.signal_pipeline")

    def process_validation_id(
        self, validation_id: str, *, experiment_id: str | None = None
    ) -> SignalProcessingOutcome:
        validation = self.validation_repository.get(validation_id)
        if validation is None:
            return SignalProcessingOutcome(validation_id, False, error="validation result not found")
        coa_result = self.coa_result_repository.get(validation.coa_result_id)
        if coa_result is None:
            return SignalProcessingOutcome(validation_id, False, error="linked COA result not found")
        snapshot = self.snapshot_repository.get(validation.snapshot_id)
        if snapshot is None:
            return SignalProcessingOutcome(validation_id, False, error="linked snapshot not found")
        emit_snapshot_event(
            self.logger, "signal_started", validation_id=validation_id,
            snapshot_id=validation.snapshot_id, session_id=validation.session_id,
            confidence=validation.overall_score, signal_version=self.signal_engine.signal_version,
        )
        try:
            signal = self.signal_engine.generate(
                snapshot, coa_result, validation, experiment_id=experiment_id
            )
            stored = self.signal_repository.insert_signal(signal)
        except Exception as exc:
            self.snapshot_repository.record_event(
                "signal_generation_failed", "ERROR",
                {"validation_id": validation_id, "coa_result_id": validation.coa_result_id,
                 "snapshot_id": validation.snapshot_id, "session_id": validation.session_id,
                 "signal_version": self.signal_engine.signal_version, "error": str(exc)},
                snapshot.get("instrument"),
            )
            emit_snapshot_event(
                self.logger, "signal_generation_failed", validation_id=validation_id, error=str(exc)
            )
            return SignalProcessingOutcome(validation_id, False, error=str(exc))
        emit_snapshot_event(
            self.logger, "signal_generated", signal_id=stored.signal_id,
            validation_id=validation_id, session_id=stored.session_id,
            confidence=stored.confidence_score, processing_time_ms=stored.processing_time_ms,
        )
        emit_snapshot_event(
            self.logger, "signal_stored", signal_id=stored.signal_id,
            validation_id=validation_id, signal_type=stored.signal_type,
        )
        return SignalProcessingOutcome(validation_id, True, signal=stored)

    def process_session(
        self, session_id: str, *, experiment_id: str | None = None
    ) -> list[SignalProcessingOutcome]:
        return [
            self.process_validation_id(validation.validation_id, experiment_id=experiment_id)
            for validation in self.validation_repository.list_by_session(session_id)
        ]
