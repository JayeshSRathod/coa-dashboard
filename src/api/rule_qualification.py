"""Read-only API facade for CQRP shadow rule qualifications."""

from __future__ import annotations

from src.rule_qualification.service import RuleQualificationService


class RuleQualificationApiV1:
    prefix = "/api/v1/rule-qualification"

    def __init__(self, service: RuleQualificationService) -> None:
        self.service = service

    def get(self, qualification_id: str) -> dict:
        record = self.service.get(qualification_id)
        return {"status": 200 if record else 404, "data": record, "mode": "SHADOW_RULE_ONLY"}

    def latest_for_pattern(self, pattern_id: str) -> dict:
        record = self.service.latest_for_pattern(pattern_id)
        return {"status": 200 if record else 404, "data": record, "mode": "SHADOW_RULE_ONLY"}

    def list(self, *, status: str | None = None, recommendation: str | None = None, limit: int = 100) -> dict:
        rows = self.service.list(status=status, recommendation=recommendation, limit=limit)
        return {"status": 200, "data": rows, "count": len(rows), "mode": "SHADOW_RULE_ONLY"}

    def qualified(self, *, limit: int = 100) -> dict:
        return self.list(status="QUALIFIED", limit=limit)

    def conditional(self, *, limit: int = 100) -> dict:
        return self.list(status="CONDITIONAL", limit=limit)

    def rejected(self, *, limit: int = 100) -> dict:
        return self.list(status="REJECTED", limit=limit)
