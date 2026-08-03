"""Serializable read-only API facade for CQRP plan revalidation."""

from __future__ import annotations

from src.premarket_validation.service import PreMarketValidationService


class PreMarketValidationApiV1:
    prefix = "/api/v1/plan-validations"

    def __init__(self, service: PreMarketValidationService) -> None:
        self.service = service

    def latest(self, trade_plan_id: str) -> dict:
        record = self.service.latest_for_plan(trade_plan_id)
        return {"status": 200 if record else 404, "data": record, "mode": "SHADOW_PAPER_ONLY"}

    def history(
        self,
        *,
        trade_plan_id: str | None = None,
        planning_horizon: str | None = None,
        validation_result: str | None = None,
        limit: int = 100,
    ) -> dict:
        rows = self.service.history(
            trade_plan_id=trade_plan_id,
            planning_horizon=planning_horizon,
            validation_result=validation_result,
            limit=limit,
        )
        return {"status": 200, "data": rows, "count": len(rows), "mode": "SHADOW_PAPER_ONLY"}
