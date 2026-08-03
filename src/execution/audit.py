"""Immutable governance audit records for CQRP shadow execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExecutionAuditRecord:
    audit_id: str
    trade_plan_id: str
    validation_id: str | None
    signal_id: str | None
    snapshot_id: str | None
    instrument: str
    planning_horizon: str
    policy_allowed: bool
    execution_eligible: bool
    action: str
    paper_trade_id: str | None
    reasons: tuple[str, ...]
    evidence: Mapping[str, Any]
    created_at: str
    created_by: str = "ShadowExecutionOrchestrator"

    @classmethod
    def new(cls, **values: Any) -> "ExecutionAuditRecord":
        values.setdefault("audit_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "ShadowExecutionOrchestrator")
        values["reasons"] = tuple(values.get("reasons", ()))
        values["evidence"] = MappingProxyType(dict(values.get("evidence", {})))
        values["planning_horizon"] = str(values["planning_horizon"]).upper()
        if values["planning_horizon"] not in {"NEXT_SESSION", "INTRADAY"}:
            raise ValueError("unsupported planning_horizon")
        if values["action"] not in {
            "BLOCK_PAPER_EXECUTION",
            "DO_NOT_EXECUTE",
            "CREATE_PAPER_TRADE",
            "PAPER_TRADE_PERSISTED",
        }:
            raise ValueError("unsupported execution audit action")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "trade_plan_id": self.trade_plan_id,
            "validation_id": self.validation_id,
            "signal_id": self.signal_id,
            "snapshot_id": self.snapshot_id,
            "instrument": self.instrument,
            "planning_horizon": self.planning_horizon,
            "policy_allowed": self.policy_allowed,
            "execution_eligible": self.execution_eligible,
            "action": self.action,
            "paper_trade_id": self.paper_trade_id,
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
