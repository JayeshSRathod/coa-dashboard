"""Application service joining existing CQRP evidence to the trade planner.

This service reads the already-persisted snapshot, COA, validation, signal and
risk decision. It creates one idempotent preliminary PAPER plan per snapshot and
planner version. It has no broker or execution dependency.
"""

from __future__ import annotations

from typing import Any, Protocol

from .engine import TradePlanningEngine
from .models import TradePlan, TradePlanningInput
from src.persistence.trade_plan_repository import TradePlanRepository


class TradePlanningEvidenceSource(Protocol):
    """Read-only contract implemented by the existing CQRP research service."""

    def latest(self, instrument_id: str) -> Any | None: ...

    def latest_snapshot(self, instrument_id: str) -> dict[str, Any] | None: ...

    def risk_decision_for_signal(self, signal: Any | None) -> Any | None: ...


class TradePlanningService:
    """Create and persist one preliminary plan per snapshot and planner version."""

    def __init__(self, source: TradePlanningEvidenceSource,
                 repository: TradePlanRepository,
                 engine: TradePlanningEngine | None = None) -> None:
        self.source = source
        self.repository = repository
        self.engine = engine or TradePlanningEngine()

    def create_latest(self, instrument: str) -> TradePlan | None:
        latest = self.source.latest(instrument)
        snapshot = self.source.latest_snapshot(instrument)
        if latest is None or snapshot is None:
            return None
        snapshot_id = str(snapshot.get("snapshot_id") or getattr(latest, "snapshot_id", ""))
        if not snapshot_id:
            return None
        existing = self.repository.get_for_snapshot(snapshot_id, self.engine.version)
        if existing is not None:
            return self._from_record(existing)

        coa = getattr(latest, "coa_result", None)
        validation = getattr(latest, "validation_result", None)
        signal = getattr(latest, "signal", None)
        risk = self.source.risk_decision_for_signal(signal)
        planning_input = self._build_input(snapshot, coa, validation, signal, risk)
        plan = self.engine.plan(planning_input)
        self.repository.append(plan)
        return plan

    def latest_plan(self, instrument: str) -> dict[str, Any] | None:
        return self.repository.latest(instrument)

    def list_plans(self, *, instrument: str | None = None,
                   readiness: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list(instrument=instrument, readiness=readiness, limit=limit)

    @staticmethod
    def _build_input(snapshot: dict[str, Any], coa: Any | None,
                     validation: Any | None, signal: Any | None,
                     risk: Any | None) -> TradePlanningInput:
        raw_output = dict(getattr(coa, "raw_output", {}) or {})
        technical = raw_output.get("technical_confirmation") or raw_output.get("technical") or {}
        momentum = getattr(signal, "momentum", None) or raw_output.get("momentum") or {}
        signal_type = getattr(signal, "signal_type", None)
        direction = getattr(signal, "direction", None)
        return TradePlanningInput(
            snapshot_id=str(snapshot["snapshot_id"]),
            signal_id=getattr(signal, "signal_id", None),
            risk_decision_id=getattr(risk, "decision_id", None),
            instrument=str(snapshot.get("instrument") or getattr(signal, "instrument", "")),
            expiry=snapshot.get("expiry") or getattr(signal, "expiry", None),
            spot=float(snapshot.get("spot") or 0.0),
            scenario_number=getattr(coa, "scenario_number", None),
            scenario=getattr(coa, "scenario", None),
            risk_mode=getattr(coa, "risk_mode", None),
            support=getattr(coa, "support", None),
            resistance=getattr(coa, "resistance", None),
            eos=getattr(coa, "eos", None),
            eor=getattr(coa, "eor", None),
            direction=direction,
            signal_type=signal_type,
            entry=getattr(signal, "entry_price", None),
            stop_loss=getattr(signal, "stop_loss", None),
            target_1=getattr(signal, "target_1", None),
            target_2=getattr(signal, "target_2", None),
            confidence_score=float(getattr(signal, "confidence_score", 0.0) or 0.0),
            validation_passed=bool(getattr(validation, "is_valid", False)),
            technical_status=TradePlanningService._mapping_value(technical, "status", "state"),
            technical_bias=TradePlanningService._mapping_value(technical, "bias", "direction"),
            momentum_state=TradePlanningService._mapping_value(momentum, "state", "classification", "bias"),
            evidence={
                "coa_result_id": getattr(coa, "coa_result_id", None),
                "validation_id": getattr(validation, "validation_id", None),
                "validation_score": getattr(validation, "overall_score", None),
                "confidence_band": getattr(signal, "confidence_band", None),
                "risk_decision": getattr(risk, "decision", None),
                "risk_reason": getattr(risk, "rejection_reason", None),
                "market_captured_at": snapshot.get("market_captured_at"),
                "session_id": snapshot.get("session_id") or getattr(signal, "session_id", None),
            },
        )

    @staticmethod
    def _mapping_value(source: Any, *keys: str) -> str | None:
        if source is None:
            return None
        if hasattr(source, "get"):
            for key in keys:
                value = source.get(key)
                if value is not None:
                    return str(value)
        for key in keys:
            value = getattr(source, key, None)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _from_record(record: dict[str, Any]) -> TradePlan:
        """Rehydrate an immutable domain object from the repository read model."""
        from .models import OpeningPlan

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
