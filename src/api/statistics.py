"""Read-only API facade for CQRP statistics snapshots."""

from __future__ import annotations

from src.statistics.service import StatisticsService


class StatisticsApiV1:
    prefix = "/api/v1/statistics"

    def __init__(self, service: StatisticsService) -> None:
        self.service = service

    def latest(self, scope_type: str = "PORTFOLIO", scope_value: str = "ALL") -> dict:
        record = self.service.latest(scope_type, scope_value)
        return {
            "status": 200 if record else 404,
            "data": record,
            "mode": "SHADOW_PAPER_ONLY",
        }

    def history(self, scope_type: str, scope_value: str, limit: int = 100) -> dict:
        rows = self.service.history(scope_type, scope_value, limit)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_PAPER_ONLY",
        }
