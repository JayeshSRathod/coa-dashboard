"""Immutable inputs and outputs for CQRP performance analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CompletedTrade:
    trade_id: str
    session_id: str
    experiment_id: str | None
    strategy_version: str
    instrument: str
    expiry: str | None
    direction: str
    scenario: str | None
    confidence_band: str | None
    confidence_score: float | None
    quantity: int
    entry_price: float | None
    exit_price: float | None
    opened_at: str
    closed_at: str
    realized_pnl: float
    mae: float = 0.0
    mfe: float = 0.0


@dataclass(frozen=True)
class AnalyticsReport:
    report_id: str
    report_type: str
    analytics_version: str
    scope: Mapping[str, Any]
    source_fingerprint: str
    metrics: Mapping[str, Any]
    groups: Mapping[str, Any]
    created_at: str = field(default_factory=_now)
    created_by: str = "PerformanceAnalyticsEngine"

    @classmethod
    def new(cls, **values: Any) -> "AnalyticsReport":
        values.setdefault("report_id", str(uuid4()))
        values.setdefault("created_at", _now())
        for key in ("scope", "metrics", "groups"):
            values[key] = MappingProxyType(dict(values.get(key, {})))
        return cls(**values)


@dataclass(frozen=True)
class PerformanceSnapshot:
    performance_snapshot_id: str
    report_id: str
    observed_at: str
    equity: float
    drawdown: float
    pnl: float
    portfolio_id: str | None = None
    session_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def new(cls, **values: Any) -> "PerformanceSnapshot":
        values.setdefault("performance_snapshot_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["payload"] = MappingProxyType(dict(values.get("payload", {})))
        return cls(**values)
