"""Governed PAPER execution manager for validated CQRP trade plans.

This manager is deliberately broker-free. It accepts only a persisted trade
plan plus a persisted pre-market validation outcome, applies deterministic
eligibility gates, and delegates trade creation to the existing
PaperExecutionEngine. Assisted and live execution remain out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from src.signal.models import ResearchSignal
from src.trade_planning.models import TradePlan

from .engine import PaperExecutionEngine
from .models import PaperTrade, TradeEvent


@dataclass(frozen=True)
class ExecutionDecision:
    eligible: bool
    action: str
    selected_plan: str | None
    reasons: tuple[str, ...]
    evidence: Mapping[str, Any]

    @classmethod
    def build(cls, *, eligible: bool, action: str,
              selected_plan: str | None, reasons: list[str],
              evidence: Mapping[str, Any]) -> "ExecutionDecision":
        return cls(
            eligible=eligible,
            action=action,
            selected_plan=selected_plan,
            reasons=tuple(reasons),
            evidence=MappingProxyType(dict(evidence)),
        )


class ExecutionManager:
    """Gate and create PAPER trades from validated trade-plan evidence."""

    version = "execution-manager-v1"

    def __init__(self, paper_engine: PaperExecutionEngine | None = None) -> None:
        self.paper_engine = paper_engine or PaperExecutionEngine()

    def assess(self, plan: TradePlan, premarket_validation: Mapping[str, Any] | None) -> ExecutionDecision:
        reasons: list[str] = []
        validation = dict(premarket_validation or {})
        selected_plan = validation.get("selected_plan")
        validation_result = str(validation.get("validation_result") or "MISSING").upper()

        if plan.status in {"CANCELLED", "EXPIRED"}:
            reasons.append(f"Trade plan status is {plan.status}.")
        if plan.readiness not in {"READY", "CONDITIONAL"}:
            reasons.append(f"Trade plan readiness is {plan.readiness}.")
        if plan.direction not in {"BUY", "SELL"}:
            reasons.append("Trade plan has no executable direction.")
        if None in {plan.entry, plan.stop_loss, plan.target_1, plan.target_2}:
            reasons.append("Trade plan is missing one or more required levels.")
        if validation_result not in {"VALIDATED", "MODIFIED"}:
            reasons.append("Pre-market validation has not approved this plan.")
        if selected_plan not in {"A", "B"}:
            reasons.append("Only opening Plan A or Plan B can create a PAPER trade.")
        if str(validation.get("risk_status") or "PASS").upper() not in {"PASS", "APPROVED", "REDUCED_SIZE"}:
            reasons.append("Risk validation did not pass.")
        if str(validation.get("data_quality") or "PASS").upper() not in {"PASS", "HEALTHY"}:
            reasons.append("Pre-market data quality did not pass.")

        eligible = not reasons
        return ExecutionDecision.build(
            eligible=eligible,
            action="CREATE_PAPER_TRADE" if eligible else "DO_NOT_EXECUTE",
            selected_plan=str(selected_plan) if selected_plan is not None else None,
            reasons=reasons or ["Validated PAPER-only execution candidate."],
            evidence={
                "trade_plan_id": plan.trade_plan_id,
                "trade_plan_status": plan.status,
                "trade_plan_readiness": plan.readiness,
                "premarket_validation_id": validation.get("validation_id"),
                "premarket_validation_result": validation_result,
                "selected_plan": selected_plan,
                "execution_manager_version": self.version,
            },
        )

    def create_paper_trade(self, *, plan: TradePlan,
                           premarket_validation: Mapping[str, Any] | None,
                           signal: ResearchSignal,
                           snapshot: Mapping[str, Any],
                           experiment_id: str | None = None,
                           ) -> tuple[ExecutionDecision, PaperTrade | None, list[TradeEvent]]:
        """Create a PAPER trade only after all execution-intelligence gates pass."""
        decision = self.assess(plan, premarket_validation)
        if not decision.eligible:
            return decision, None, []
        if signal.signal_id != plan.signal_id:
            mismatch = ExecutionDecision.build(
                eligible=False,
                action="DO_NOT_EXECUTE",
                selected_plan=decision.selected_plan,
                reasons=["Signal identity does not match the persisted Trade Plan."],
                evidence={**dict(decision.evidence), "signal_id": signal.signal_id},
            )
            return mismatch, None, []
        if str(snapshot.get("instrument") or "") != plan.instrument:
            mismatch = ExecutionDecision.build(
                eligible=False,
                action="DO_NOT_EXECUTE",
                selected_plan=decision.selected_plan,
                reasons=["Snapshot instrument does not match the persisted Trade Plan."],
                evidence={**dict(decision.evidence), "snapshot_id": snapshot.get("snapshot_id")},
            )
            return mismatch, None, []
        trade, events = self.paper_engine.create_trade(
            signal, snapshot, experiment_id=experiment_id
        )
        return decision, trade, events
