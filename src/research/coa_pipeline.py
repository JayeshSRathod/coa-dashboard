"""Application service that runs a versioned analysis engine over persisted snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
import logging
from typing import Any

from src.coa.contracts import AnalysisEngine
from src.coa.models import COAResearchResult
from src.persistence.coa_result_repository import COAResultRepository
from src.persistence.snapshot_repository import SnapshotRepository

from .observability import emit_snapshot_event


@dataclass(frozen=True)
class COAProcessingOutcome:
    snapshot_id: str
    success: bool
    result: COAResearchResult | None = None
    error: str | None = None


class COAResearchPipeline:
    """Coordinates snapshot loading, deterministic analysis, and result persistence."""

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        result_repository: COAResultRepository,
        analysis_engine: AnalysisEngine,
        logger: logging.Logger | None = None,
    ) -> None:
        self.snapshot_repository = snapshot_repository
        self.result_repository = result_repository
        self.analysis_engine = analysis_engine
        self.logger = logger or logging.getLogger("cqrp.coa_pipeline")

    def process_snapshot_id(
        self, snapshot_id: str, *, experiment_id: str | None = None
    ) -> COAProcessingOutcome:
        snapshot = self.snapshot_repository.get(snapshot_id)
        if snapshot is None:
            return COAProcessingOutcome(snapshot_id, False, error="snapshot not found")
        return self.process_snapshot(snapshot, experiment_id=experiment_id)

    def process_snapshot(
        self, snapshot: dict[str, Any], *, experiment_id: str | None = None
    ) -> COAProcessingOutcome:
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        session_id = str(snapshot.get("session_id") or "")
        started = perf_counter()
        emit_snapshot_event(
            self.logger, "coa_analysis_started", snapshot_id=snapshot_id,
            session_id=session_id, experiment_id=experiment_id,
            engine_version=self.analysis_engine.engine_version,
        )
        try:
            result = self.analysis_engine.analyze(snapshot, experiment_id=experiment_id)
            stored = self.result_repository.append(result)
        except Exception as exc:
            self.snapshot_repository.record_event(
                "coa_analysis_failed", "ERROR",
                {"snapshot_id": snapshot_id, "session_id": session_id,
                 "experiment_id": experiment_id, "engine_version": self.analysis_engine.engine_version,
                 "error": str(exc)},
                snapshot.get("instrument"),
            )
            emit_snapshot_event(
                self.logger, "coa_analysis_failed", snapshot_id=snapshot_id,
                session_id=session_id, experiment_id=experiment_id,
                engine_version=self.analysis_engine.engine_version, error=str(exc),
            )
            return COAProcessingOutcome(snapshot_id, False, error=str(exc))
        duration_ms = (perf_counter() - started) * 1000
        emit_snapshot_event(
            self.logger, "coa_analysis_completed", snapshot_id=snapshot_id,
            session_id=session_id, experiment_id=experiment_id,
            engine_version=stored.engine_version, result_id=stored.coa_result_id,
            processing_duration_ms=duration_ms,
        )
        return COAProcessingOutcome(snapshot_id, True, result=stored)

    def process_session(
        self, session_id: str, *, experiment_id: str | None = None
    ) -> list[COAProcessingOutcome]:
        return [
            self.process_snapshot(snapshot, experiment_id=experiment_id)
            for snapshot in self.snapshot_repository.list_by_session(session_id)
        ]

    def process_time_range(
        self, instrument: str, start: str, end: str, *, experiment_id: str | None = None
    ) -> list[COAProcessingOutcome]:
        return [
            self.process_snapshot(snapshot, experiment_id=experiment_id)
            for snapshot in self.snapshot_repository.list_by_time_range(instrument, start, end)
        ]
