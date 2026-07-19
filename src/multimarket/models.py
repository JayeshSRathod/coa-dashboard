"""Immutable business entities for instruments, accounts, routes, and provider results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    exchange: str
    segment: str
    symbol: str
    trading_symbol: str
    lot_size: int
    tick_size: float
    currency: str
    status: str
    isin: str | None = None
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    margin_group: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    created_by: str = "InstrumentRegistry"

    @classmethod
    def new(cls, **values: Any) -> "Instrument":
        values.setdefault("instrument_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["metadata"] = MappingProxyType(dict(values.get("metadata", {})))
        return cls(**values)


@dataclass(frozen=True)
class BrokerAccount:
    account_id: str
    broker_name: str
    client_id: str
    display_name: str
    status: str
    permissions: Mapping[str, Any] = field(default_factory=dict)
    execution_enabled: bool = False
    default_portfolio_id: str | None = None
    last_sync_at: str | None = None
    created_at: str = field(default_factory=_now)
    created_by: str = "MultiBrokerFramework"

    @classmethod
    def new(cls, **values: Any) -> "BrokerAccount":
        values.setdefault("account_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["permissions"] = MappingProxyType(dict(values.get("permissions", {})))
        return cls(**values)


@dataclass(frozen=True)
class ExecutionRoute:
    route_id: str
    portfolio_id: str
    account_id: str
    broker_name: str
    priority: int
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    created_by: str = "ExecutionRouter"

    @classmethod
    def new(cls, **values: Any) -> "ExecutionRoute":
        values.setdefault("route_id", str(uuid4()))
        values.setdefault("created_at", _now())
        return cls(**values)


@dataclass(frozen=True)
class RoutingDecision:
    portfolio_id: str
    account_id: str | None
    broker_name: str | None
    route_id: str | None
    reason: str
