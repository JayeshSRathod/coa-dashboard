"""Deterministic evidence construction from completed CQRP PAPER trades."""

from __future__ import annotations

from typing import Any, Mapping

from src.execution.lifecycle import PaperTradeLifecycleSummary

from .models import EvidenceRecord


class EvidenceEngine:
    version = "evidence-v1"

    def build(
        self,
        *,
        trade: Mapping[str, Any],
        lifecycle: PaperTradeLifecycleSummary | Mapping[str, Any],
        plan: Mapping[str, Any] | None = None,
        validation: Mapping[str, Any] | None = None,
        execution_audit: Mapping[str, Any] | None = None,
        signal: Mapping[str, Any] | None = None,
        snapshot: Mapping[str, Any] | None = None,
        regime: str | None = None,
    ) -> EvidenceRecord:
        lifecycle_data = lifecycle.as_dict() if hasattr(lifecycle, "as_dict") else dict(lifecycle)
        plan_data = dict(plan or {})
        validation_data = dict(validation or {})
        audit_data = dict(execution_audit or {})
        signal_data = dict(signal or {})
        snapshot_data = dict(snapshot or {})

        status = str(lifecycle_data.get("status") or "").upper()
        if status not in {"CLOSED", "CANCELLED", "EXPIRED"}:
            raise ValueError("evidence can only be created for terminal PAPER trades")

        realized_pnl = float(lifecycle_data.get("realized_pnl") or 0.0)
        outcome = self._outcome(status, realized_pnl)
        direction = str(trade.get("direction") or plan_data.get("direction") or "").upper()
        if direction not in {"BUY", "SELL"}:
            raise ValueError("evidence requires BUY or SELL direction")

        feature_vector = {
            "market_bias": plan_data.get("market_bias"),
            "expected_opening": plan_data.get("expected_opening"),
            "readiness": plan_data.get("readiness"),
            "validation_result": validation_data.get("validation_result"),
            "opening_classification": validation_data.get("opening_classification"),
            "risk_status": validation_data.get("risk_status"),
            "data_quality": validation_data.get("data_quality"),
            "technical_status": snapshot_data.get("technical_status"),
            "technical_bias": snapshot_data.get("technical_bias"),
            "momentum_state": snapshot_data.get("momentum_state"),
            "gap_pct": (validation_data.get("evidence") or {}).get("gap_pct"),
            "target_1_hit": (lifecycle_data.get("metrics") or {}).get("target_1_hit"),
            "target_2_hit": (lifecycle_data.get("metrics") or {}).get("target_2_hit"),
            "trailing_activated": (lifecycle_data.get("metrics") or {}).get("trailing_activated"),
            "event_count": lifecycle_data.get("event_count"),
        }
        lineage = {
            "trade_id": trade.get("trade_id"),
            "trade_plan_id": plan_data.get("trade_plan_id"),
            "validation_id": validation_data.get("validation_id"),
            "execution_audit_id": audit_data.get("audit_id"),
            "signal_id": signal_data.get("signal_id") or trade.get("signal_id"),
            "snapshot_id": snapshot_data.get("snapshot_id") or trade.get("snapshot_id"),
            "experiment_id": trade.get("experiment_id"),
            "strategy_version": trade.get("strategy_version"),
            "execution_version": trade.get("execution_version"),
            "lifecycle_version": (lifecycle_data.get("metrics") or {}).get("lifecycle_version"),
        }

        return EvidenceRecord.new(
            trade_id=str(trade["trade_id"]),
            trade_plan_id=plan_data.get("trade_plan_id"),
            validation_id=validation_data.get("validation_id"),
            execution_audit_id=audit_data.get("audit_id"),
            signal_id=signal_data.get("signal_id") or trade.get("signal_id"),
            snapshot_id=snapshot_data.get("snapshot_id") or trade.get("snapshot_id"),
            experiment_id=trade.get("experiment_id"),
            instrument=str(trade.get("instrument") or plan_data.get("instrument")),
            planning_horizon=str(plan_data.get("planning_horizon") or "INTRADAY"),
            scenario_number=signal_data.get("scenario_number") or snapshot_data.get("scenario_number"),
            scenario=signal_data.get("scenario") or snapshot_data.get("scenario"),
            direction=direction,
            outcome=outcome,
            realized_pnl=realized_pnl,
            realized_r_multiple=lifecycle_data.get("realized_r_multiple"),
            mfe=float(lifecycle_data.get("mfe") or 0.0),
            mae=float(lifecycle_data.get("mae") or 0.0),
            holding_seconds=lifecycle_data.get("holding_seconds"),
            confidence_score=validation_data.get("confidence_after", plan_data.get("confidence_score")),
            selected_plan=validation_data.get("selected_plan"),
            entry_price=lifecycle_data.get("entry_price"),
            average_exit_price=lifecycle_data.get("average_exit_price"),
            exit_reason=lifecycle_data.get("exit_reason"),
            regime=regime or snapshot_data.get("regime"),
            feature_vector=feature_vector,
            lineage=lineage,
            evidence_version=self.version,
        )

    @staticmethod
    def _outcome(status: str, realized_pnl: float) -> str:
        if status == "CANCELLED":
            return "CANCELLED"
        if status == "EXPIRED":
            return "EXPIRED"
        if realized_pnl > 0:
            return "WIN"
        if realized_pnl < 0:
            return "LOSS"
        return "BREAKEVEN"
