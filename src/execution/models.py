"""Immutable paper-trade identities, events, and projector state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    signal_id: str
    session_id: str
    snapshot_id: str
    experiment_id: str | None
    strategy_version: str
    execution_version: str
    instrument: str
    direction: str
    expiry: str | None
    strike: float | None
    option_type: str | None
    quantity: int
    intended_entry: float | None
    initial_stop_loss: float | None
    initial_target_1: float | None
    initial_target_2: float | None
    initial_trailing_reference: float | None
    created_at: str = field(default_factory=_now)
    created_by: str = "PaperExecutionEngine"

    @classmethod
    def new(cls, **values: Any) -> "PaperTrade":
        values.setdefault("trade_id", str(uuid4()))
        values.setdefault("created_at", _now())
        if values["direction"] not in {"BUY", "SELL"}:
            raise ValueError("paper trade direction must be BUY or SELL")
        if int(values["quantity"]) < 1:
            raise ValueError("paper trade quantity must be positive")
        return cls(**values)


@dataclass(frozen=True)
class TradeEvent:
    event_id: str
    trade_id: str
    session_id: str
    source_snapshot_id: str | None
    event_type: str
    occurred_at: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    created_by: str = "PaperExecutionEngine"

    @classmethod
    def new(cls, **values: Any) -> "TradeEvent":
        values.setdefault("event_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["payload"] = MappingProxyType(dict(values.get("payload", {})))
        return cls(**values)


@dataclass(frozen=True)
class TradeState:
    trade_id: str
    status: str = "PENDING"
    quantity_remaining: int = 0
    executed_entry: float | None = None
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    trailing_reference: float | None = None
    average_exit_price: float | None = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    mfe: float = 0.0
    mae: float = 0.0
    opened_at: str | None = None
    closed_at: str | None = None
    exit_reason: str | None = None
