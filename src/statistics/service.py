"""Application service for versioned CQRP statistics snapshots."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.persistence.statistics_repository import StatisticsRepository

from .engine import StatisticsEngine, StatisticsReport
from .models import StatisticsSnapshot


class StatisticsService:
    def __init__(
        self,
        repository: StatisticsRepository,
        engine: StatisticsEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or StatisticsEngine()

    def calculate(
        self,
        evidence_records: Iterable[Mapping[str, Any]],
        *,
        scope_type: str = "PORTFOLIO",
        scope_value: str = "ALL",
        persist: bool = True,
    ) -> StatisticsSnapshot:
        rows = [dict(row) for row in evidence_records]
        report: StatisticsReport = self.engine.calculate(rows)
        snapshot = StatisticsSnapshot.new(
            scope_type=scope_type,
            scope_value=scope_value,
            evidence_count=len(rows),
            report=report.as_dict(),
            statistics_version=self.engine.version,
        )
        if persist:
            self.repository.append(snapshot)
        return snapshot

    def latest(self, scope_type: str = "PORTFOLIO", scope_value: str = "ALL") -> dict[str, Any] | None:
        return self.repository.latest(scope_type, scope_value)

    def history(self, scope_type: str, scope_value: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.history(scope_type, scope_value, limit)
