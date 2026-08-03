"""Read-only API facade for CQRP pattern-discovery research artifacts."""

from __future__ import annotations

from src.pattern_discovery.service import PatternDiscoveryService


class PatternDiscoveryApiV1:
    prefix = "/api/v1/patterns"

    def __init__(self, service: PatternDiscoveryService) -> None:
        self.service = service

    def get(self, pattern_id: str) -> dict:
        record = self.service.get_pattern(pattern_id)
        return {
            "status": 200 if record else 404,
            "data": record,
            "mode": "SHADOW_RESEARCH_ONLY",
        }

    def list(
        self,
        *,
        status: str | None = None,
        experiment_id: str | None = None,
        discovery_method: str | None = None,
        limit: int = 100,
    ) -> dict:
        rows = self.service.list_patterns(
            status=status,
            experiment_id=experiment_id,
            discovery_method=discovery_method,
            limit=limit,
        )
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_RESEARCH_ONLY",
        }

    def discovered(self, *, limit: int = 100) -> dict:
        return self.list(status="DISCOVERED", limit=limit)

    def validation_pending(self, *, limit: int = 100) -> dict:
        return self.list(status="VALIDATION_PENDING", limit=limit)

    def promoted(self, *, limit: int = 100) -> dict:
        return self.list(status="PROMOTED", limit=limit)

    def rejected(self, *, limit: int = 100) -> dict:
        return self.list(status="REJECTED", limit=limit)
