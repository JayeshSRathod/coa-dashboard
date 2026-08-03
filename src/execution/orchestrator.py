"""End-to-end orchestration for CQRP shadow PAPER execution.

The orchestrator combines policy evaluation, deterministic execution eligibility,
simulated-trade persistence, and immutable audit logging. It deliberately has no
broker dependency and cannot submit live orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from src.persistence.execution_audit_repository import ExecutionAuditRepository
from src.signal.models import ResearchSignal
from src.trade_planning.models import TradePlan

from .audit import ExecutionAuditRecord
from .execution_service import ShadowExecutionResult, ShadowExecutionService
from .policy import (
    ExecutionPolicyContext,
    ExecutionPolicyDecision,
    ExecutionPolicyEngine,
)


@dataclass(frozen=True)
class OrchestratedExecutionResult:
    policy: ExecutionPolicyDecision
    execution: ShadowExecutionResult | None
    audit_id: str
    mode: str = "SHADOW_PAPER_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy": {
                "allowed": self.policy.allowed,
                "action": self.policy.action,
                "reasons": list(self.policy.reasons),
                "evidence": dict(self.policy.evidence),
            },
            "execution": self.execution.as_dict() if self.execution else None,
            "audit_id": self.audit_id,
            "mode": self.mode,
        }


class ShadowExecutionOrchestrator:
    """Coordinate policy, execution, persistence, and audit for PAPER trades."""

    version = "shadow-execution-orchestrator-v1"

    def __init__(
        self,
        execution_service: ShadowExecutionService,
        audit_repository: ExecutionAuditRepository,
        policy_engine: ExecutionPolicyEngine | None = None,
    ) -> None:
        self.execution_service = execution_service
        self.audit_repository = audit_repository
        self.policy_engine = policy_engine or ExecutionPolicyEngine()

    def run(
        self,
        *,
        plan: TradePlan,
        validation: Mapping[str, Any] | None,
        signal: ResearchSignal,
        snapshot: Mapping[str, Any],
        observed_at: datetime,
        open_trade_count: int,
        open_instrument_trade_count: int,
        daily_realized_pnl: float,
        duplicate_trade_exists: bool,
        experiment_id: str | None = None,
    ) -> OrchestratedExecutionResult:
        validation_data = dict(validation or {})
        policy_context = ExecutionPolicyContext(
            observed_at=observed_at,
            planning_horizon=plan.planning_horizon,
            instrument=plan.instrument,
            open_trade_count=open_trade_count,
            open_instrument_trade_count=open_instrument_trade_count,
            daily_realized_pnl=daily_realized_pnl,
            duplicate_trade_exists=duplicate_trade_exists,
            data_quality=str(validation_data.get("data_quality") or "PASS"),
            risk_status=str(validation_data.get("risk_status") or "PASS"),
            metadata={
                "trade_plan_id": plan.trade_plan_id,
                "validation_id": validation_data.get("validation_id"),
            },
        )
        policy = self.policy_engine.evaluate(policy_context)

        if not policy.allowed:
            audit = self._build_audit(
                plan=plan,
                validation=validation_data,
                signal=signal,
                snapshot=snapshot,
                policy=policy,
                execution=None,
                action="BLOCK_PAPER_EXECUTION",
            )
            audit_id = self.audit_repository.append(audit)
            return OrchestratedExecutionResult(
                policy=policy,
                execution=None,
                audit_id=audit_id,
            )

        execution = self.execution_service.execute(
            plan=plan,
            validation=validation_data,
            signal=signal,
            snapshot=snapshot,
            experiment_id=experiment_id,
        )
        action = (
            "PAPER_TRADE_PERSISTED"
            if execution.persisted and execution.trade is not None
            else execution.decision.action
        )
        audit = self._build_audit(
            plan=plan,
            validation=validation_data,
            signal=signal,
            snapshot=snapshot,
            policy=policy,
            execution=execution,
            action=action,
        )
        audit_id = self.audit_repository.append(audit)
        return OrchestratedExecutionResult(
            policy=policy,
            execution=execution,
            audit_id=audit_id,
        )

    def _build_audit(
        self,
        *,
        plan: TradePlan,
        validation: Mapping[str, Any],
        signal: ResearchSignal,
        snapshot: Mapping[str, Any],
        policy: ExecutionPolicyDecision,
        execution: ShadowExecutionResult | None,
        action: str,
    ) -> ExecutionAuditRecord:
        execution_decision = execution.decision if execution else None
        reasons = list(policy.reasons)
        if execution_decision is not None:
            reasons.extend(execution_decision.reasons)
        evidence = {
            **dict(policy.evidence),
            "orchestrator_version": self.version,
            "validation_result": validation.get("validation_result"),
            "selected_plan": validation.get("selected_plan"),
        }
        if execution_decision is not None:
            evidence.update(dict(execution_decision.evidence))
        return ExecutionAuditRecord.new(
            trade_plan_id=plan.trade_plan_id,
            validation_id=validation.get("validation_id"),
            signal_id=signal.signal_id,
            snapshot_id=snapshot.get("snapshot_id"),
            instrument=plan.instrument,
            planning_horizon=plan.planning_horizon,
            policy_allowed=policy.allowed,
            execution_eligible=bool(execution_decision and execution_decision.eligible),
            action=action,
            paper_trade_id=(execution.trade.trade_id if execution and execution.trade else None),
            reasons=tuple(reasons),
            evidence=evidence,
        )
