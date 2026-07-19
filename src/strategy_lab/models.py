"""Immutable strategy-lab domain records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frozen(values: dict[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    strategy_name: str
    description: str
    owner: str
    category: str
    asset_class: str
    market: str
    version: str
    status: str
    parent_strategy_id: str | None = None
    created_at: str = field(default_factory=_now)
    created_by: str = "StrategyLab"

    @classmethod
    def new(cls, **values: Any) -> "Strategy":
        values.setdefault("strategy_id", str(uuid4()))
        values.setdefault("created_at", _now())
        return cls(**values)


@dataclass(frozen=True)
class Configuration:
    configuration_id: str
    strategy_id: str
    values: Mapping[str, Any]
    checksum: str
    created_at: str = field(default_factory=_now)
    created_by: str = "StrategyLab"

    @classmethod
    def new(cls, **values: Any) -> "Configuration":
        values.setdefault("configuration_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["values"] = _frozen(values.get("values", {}))
        return cls(**values)


@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    market: str
    source: str
    symbols: tuple[str, ...]
    from_date: str
    to_date: str
    snapshot_count: int
    checksum: str
    created_at: str = field(default_factory=_now)
    created_by: str = "StrategyLab"

    @classmethod
    def new(cls, **values: Any) -> "Dataset":
        values.setdefault("dataset_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["symbols"] = tuple(values.get("symbols", ()))
        return cls(**values)


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    strategy_id: str
    experiment_name: str
    objective: str
    hypothesis: str
    dataset_id: str
    configuration_id: str
    market: str
    symbols: tuple[str, ...]
    from_date: str
    to_date: str
    execution_mode: str
    status: str = "CREATED"
    notes: str | None = None
    created_at: str = field(default_factory=_now)
    created_by: str = "StrategyLab"

    @classmethod
    def new(cls, **values: Any) -> "Experiment":
        values.setdefault("experiment_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["symbols"] = tuple(values.get("symbols", ()))
        return cls(**values)


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    experiment_id: str
    input_fingerprint: str
    status: str
    execution_time_ms: float
    results: Mapping[str, Any]
    occurred_at: str = field(default_factory=_now)
    created_at: str = field(default_factory=_now)

    @classmethod
    def new(cls, **values: Any) -> "ExperimentRun":
        values.setdefault("run_id", str(uuid4()))
        values.setdefault("occurred_at", _now())
        values.setdefault("created_at", _now())
        values["results"] = _frozen(values.get("results", {}))
        return cls(**values)
