"""Immutable order requests, identities, events, and projected lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class OrderRequest:
    client_order_key: str
    signal_id: str | None
    trade_id: str | None
    portfolio_id: str | None
    approval_reference: str | None
    broker_name: str
    exchange: str
    symbol: str
    transaction_type: str
    quantity: int
    order_type: str = "MARKET"
    product_type: str = "INTRADAY"
    price: float | None = None
    trigger_price: float | None = None
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    estimated_value: float = 0.0

    def __post_init__(self) -> None:
        if self.transaction_type not in {"BUY", "SELL"} or self.quantity < 1:
            raise ValueError("invalid transaction type or quantity")


@dataclass(frozen=True)
class ExecutionOrder:
    order_id: str
    execution_id: str
    broker_order_id: str | None
    client_order_key: str
    signal_id: str | None
    trade_id: str | None
    portfolio_id: str | None
    broker_name: str
    execution_mode: str
    exchange: str
    symbol: str
    expiry: str | None
    strike: float | None
    option_type: str | None
    order_type: str
    product_type: str
    transaction_type: str
    quantity: int
    price: float | None
    trigger_price: float | None
    created_at: str = field(default_factory=_now)
    created_by: str = "ExecutionGateway"

    @classmethod
    def new(cls, **values: Any) -> "ExecutionOrder":
        values.setdefault("order_id", str(uuid4()))
        values.setdefault("execution_id", str(uuid4()))
        values.setdefault("created_at", _now())
        return cls(**values)


@dataclass(frozen=True)
class OrderEvent:
    event_id: str
    order_id: str
    event_type: str
    occurred_at: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    created_by: str = "ExecutionGateway"

    @classmethod
    def new(cls, **values: Any) -> "OrderEvent":
        values.setdefault("event_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values.setdefault("occurred_at", _now())
        values["payload"] = MappingProxyType(dict(values.get("payload", {})))
        return cls(**values)


@dataclass(frozen=True)
class OrderState:
    order_id: str
    status: str = "CREATED"
    broker_order_id: str | None = None
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: float | None = None
    rejection_reason: str | None = None
