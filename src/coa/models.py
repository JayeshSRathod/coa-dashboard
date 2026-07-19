"""Immutable typed output of a CQRP COA research-engine execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class COAResearchResult:
    """A persisted research observation, not an executable trading signal."""

    coa_result_id: str
    snapshot_id: str
    session_id: str
    experiment_id: str | None
    strategy_version: str
    engine_version: str
    scenario_number: int | None
    scenario: str | None
    eos: float | None
    eor: float | None
    support: float | None
    resistance: float | None
    momentum: Mapping[str, Any] | None
    diversion: Mapping[str, Any] | None
    trend: str | None
    direction: str | None
    risk_mode: str | None
    raw_output: Mapping[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    market_timestamp: str = ""
    created_at: str = field(default_factory=_utc_now)
    created_by: str = "FrozenCOAAdapter"

    @classmethod
    def new(cls, **values: Any) -> "COAResearchResult":
        values.setdefault("coa_result_id", str(uuid4()))
        values.setdefault("created_at", _utc_now())
        values["raw_output"] = MappingProxyType(dict(values.get("raw_output", {})))
        for name in ("momentum", "diversion"):
            if values.get(name) is not None:
                values[name] = MappingProxyType(dict(values[name]))
        return cls(**values)

    def analytical_values(self) -> dict[str, Any]:
        """The deterministic outputs; excludes execution-specific metadata."""
        return {
            "engine_version": self.engine_version,
            "scenario_number": self.scenario_number,
            "scenario": self.scenario,
            "eos": self.eos,
            "eor": self.eor,
            "support": self.support,
            "resistance": self.resistance,
            "momentum": dict(self.momentum) if self.momentum is not None else None,
            "diversion": dict(self.diversion) if self.diversion is not None else None,
            "trend": self.trend,
            "direction": self.direction,
            "risk_mode": self.risk_mode,
            "raw_output": dict(self.raw_output),
        }
