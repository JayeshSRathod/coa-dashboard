"""Application service for CQRP research-only pattern discovery."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.persistence.pattern_repository import PatternRepository

from .engine import PatternDiscoveryEngine
from .models import PatternCandidate


class PatternDiscoveryService:
    def __init__(
        self,
        repository: PatternRepository,
        engine: PatternDiscoveryEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or PatternDiscoveryEngine()

    def discover(
        self,
        evidence_records: Iterable[Mapping[str, Any]],
        *,
        experiment_id: str | None = None,
        source_run_id: str | None = None,
        statistics_snapshot_id: str | None = None,
        minimum_sample_size: int = 20,
        minimum_uplift: float = 5.0,
    ) -> list[dict[str, Any]]:
        candidates = self.engine.discover(
            evidence_records,
            experiment_id=experiment_id,
            source_run_id=source_run_id,
            statistics_snapshot_id=statistics_snapshot_id,
            minimum_sample_size=minimum_sample_size,
            minimum_uplift=minimum_uplift,
        )
        rows: list[dict[str, Any]] = []
        for candidate in candidates:
            self.repository.append(candidate)
            rows.append(candidate.as_dict())
        return rows

    def get(self, pattern_id: str) -> dict[str, Any] | None:
        return self.repository.get(pattern_id)

    def list(
        self,
        *,
        status: str | None = None,
        experiment_id: str | None = None,
        discovery_method: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.repository.list(
            status=status,
            experiment_id=experiment_id,
            discovery_method=discovery_method,
            limit=limit,
        )

    @staticmethod
    def rehydrate(record: Mapping[str, Any]) -> PatternCandidate:
        return PatternCandidate.new(**dict(record))
