"""Immutable evidence records for completed CQRP shadow PAPER trades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    trade_id: str
    trade_plan_id: str | None
    validation_id: str | None
    execution_audit_id: str | None
    signal_id: str | None
    snapshot_id: str | None
    experiment_id: str | None
    instrument: str
    planning_horizon: str
    scenario_number: int | None
    scenario: str | None
    direction: str
    outcome: str
    realized_pnl: float
    realized_r_multiple: float | None
    mfe: float
    mae: float
    holding_seconds: float | None
    confidence_score: float | None
    selected_plan: str | None
    entry_price: float | None
    average_exit_price: float | None
    exit_reason: str | None
    regime: str | None
    feature_vector: Mapping[str, Any]
    lineage: Mapping[str, Any]
    evidence_version: str
    created_at: str
    created_by: str = "EvidenceEngine"

    @classmethod
    def new(cls, **values: Any) -> "EvidenceRecord":
        values.setdefault("evidence_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "EvidenceEngine")
        values.setdefault("evidence_version", "evidence-v1")
        values["planning_horizon"] = str(values["planning_horizon"]).upper()
        values["direction"] = str(values["direction"]).upper()
        values["outcome"] = str(values["outcome"]).upper()
        values["feature_vector"] = MappingProxyType(dict(values.get("feature_vector", {})))
        values["lineage"] = MappingProxyType(dict(values.get("lineage", {})))

        if values["planning_horizon"] not in {"NEXT_SESSION", "INTRADAY"}:
            raise ValueError("unsupported planning_horizon")
        if values["direction"] not in {"BUY", "SELL"}:
            raise ValueError("direction must be BUY or SELL")
        if values["outcome"] not in {"WIN", "LOSS", "BREAKEVEN", "CANCELLED", "EXPIRED"}:
            raise ValueError("unsupported evidence outcome")
        if values.get("selected_plan") not in {None, "A", "B", "C"}:
            raise ValueError("selected_plan must be A, B, C, or None")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "trade_id": self.trade_id,
            "trade_plan_id": self.trade_plan_id,
            "validation_id": self.validation_id,
            "execution_audit_id": self.execution_audit_id,
            "signal_id": self.signal_id,
            "snapshot_id": self.snapshot_id,
            "experiment_id": self.experiment_id,
            "instrument": self.instrument,
            "planning_horizon": self.planning_horizon,
            "scenario_number": self.scenario_number,
            "scenario": self.scenario,
            "direction": self.direction,
            "outcome": self.outcome,
            "realized_pnl": round(float(self.realized_pnl), 8),
            "realized_r_multiple": self.realized_r_multiple,
            "mfe": round(float(self.mfe), 8),
            "mae": round(float(self.mae), 8),
            "holding_seconds": self.holding_seconds,
            "confidence_score": self.confidence_score,
            "selected_plan": self.selected_plan,
            "entry_price": self.entry_price,
            "average_exit_price": self.average_exit_price,
            "exit_reason": self.exit_reason,
            "regime": self.regime,
            "feature_vector": dict(self.feature_vector),
            "lineage": dict(self.lineage),
            "evidence_version": self.evidence_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
