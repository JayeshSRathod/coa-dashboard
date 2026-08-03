"""Read-only API facade for CQRP shadow execution intelligence."""

from __future__ import annotations

from src.persistence.execution_audit_repository import ExecutionAuditRepository


class ExecutionIntelligenceApiV1:
    prefix = "/api/v1/execution-intelligence"

    def __init__(self, audits: ExecutionAuditRepository) -> None:
        self.audits = audits

    def latest_for_plan(self, trade_plan_id: str) -> dict:
        record = self.audits.latest_for_plan(trade_plan_id)
        return {
            "status": 200 if record else 404,
            "data": record,
            "mode": "SHADOW_PAPER_ONLY",
        }

    def history(
        self,
        *,
        trade_plan_id: str | None = None,
        action: str | None = None,
        instrument: str | None = None,
        limit: int = 100,
    ) -> dict:
        rows = self.audits.list(
            trade_plan_id=trade_plan_id,
            action=action,
            instrument=instrument,
            limit=limit,
        )
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_PAPER_ONLY",
        }

    def blocked(self, *, limit: int = 100) -> dict:
        rows = self.audits.list(action="BLOCK_PAPER_EXECUTION", limit=limit)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_PAPER_ONLY",
        }

    def executed(self, *, limit: int = 100) -> dict:
        rows = self.audits.list(action="PAPER_TRADE_PERSISTED", limit=limit)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_PAPER_ONLY",
        }
