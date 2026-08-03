"""Application service for idempotent CQRP plan revalidation.

The service remains downstream of the persisted research pipeline. It receives
a TradePlan and a fresh PreMarketObservation, invokes the deterministic engine,
and persists one immutable result per observed snapshot and validator version.
"""

from __future__ import annotations

from typing import Any

from src.persistence.premarket_validation_repository import PreMarketValidationRepository
from src.trade_planning.models import OpeningPlan, TradePlan

from .engine import PreMarketValidationEngine
from .models import PreMarketObservation, PreMarketValidationResult


class PreMarketValidationService:
    """Orchestrate deterministic, append-only next-session/intraday validation."""

    def __init__(
        self,
        repository: PreMarketValidationRepository,
        engine: PreMarketValidationEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or PreMarketValidationEngine()

    def validate(
        self,
        plan: TradePlan,
        observation: PreMarketObservation,
    ) -> PreMarketValidationResult:
        existing = self.repository.get_for_observation(
            plan.trade_plan_id,
            observation.snapshot_id,
            self.engine.version,
        )
        if existing is not None:
            return self._from_record(existing)
        result = self.engine.validate(plan, observation)
        self.repository.append(result)
        return result

    def latest_for_plan(self, trade_plan_id: str) -> dict[str, Any] | None:
        return self.repository.latest_for_plan(trade_plan_id)

    def history(
        self,
        *,
        trade_plan_id: str | None = None,
        planning_horizon: str | None = None,
        validation_result: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.repository.list(
            trade_plan_id=trade_plan_id,
            planning_horizon=planning_horizon,
            validation_result=validation_result,
            limit=limit,
        )

    @staticmethod
    def plan_from_record(record: dict[str, Any]) -> TradePlan:
        return TradePlan.new(
            trade_plan_id=record["trade_plan_id"],
            snapshot_id=record["snapshot_id"],
            signal_id=record.get("signal_id"),
            risk_decision_id=record.get("risk_decision_id"),
            instrument=record["instrument"],
            expiry=record.get("expiry"),
            planning_horizon=record["planning_horizon"],
            market_bias=record["market_bias"],
            expected_opening=record["expected_opening"],
            direction=record.get("direction"),
            option_type=record.get("option_type"),
            entry=record.get("entry"),
            stop_loss=record.get("stop_loss"),
            target_1=record.get("target_1"),
            target_2=record.get("target_2"),
            confidence_score=record["confidence_score"],
            readiness=record["readiness"],
            status=record["status"],
            valid_for_session=record.get("valid_for_session"),
            rationale=tuple(record.get("rationale", ())),
            warnings=tuple(record.get("warnings", ())),
            opening_plans=tuple(OpeningPlan(**item) for item in record.get("opening_plans", ())),
            evidence=record.get("evidence", {}),
            planner_version=record["planner_version"],
            created_at=record["created_at"],
            created_by=record.get("created_by", "TradePlanningEngine"),
        )

    @staticmethod
    def _from_record(record: dict[str, Any]) -> PreMarketValidationResult:
        return PreMarketValidationResult.new(
            validation_id=record["validation_id"],
            trade_plan_id=record["trade_plan_id"],
            source_snapshot_id=record["source_snapshot_id"],
            observed_snapshot_id=record["observed_snapshot_id"],
            planning_horizon=record["planning_horizon"],
            validation_result=record["validation_result"],
            selected_plan=record.get("selected_plan"),
            opening_classification=record["opening_classification"],
            confidence_before=record["confidence_before"],
            confidence_after=record["confidence_after"],
            risk_status=record["risk_status"],
            data_quality=record["data_quality"],
            reasons=tuple(record.get("reasons", ())),
            warnings=tuple(record.get("warnings", ())),
            evidence=record.get("evidence", {}),
            validator_version=record["validator_version"],
            created_at=record["created_at"],
            created_by=record.get("created_by", "PreMarketValidationEngine"),
        )
