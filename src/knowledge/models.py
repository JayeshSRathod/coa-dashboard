"""Immutable records used by the deterministic Research Knowledge Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frozen(values: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True)
class KnowledgeFact:
    fact_id: str
    source_run_id: str
    domain: str
    subject_type: str
    subject_key: str
    strategy_id: str | None
    experiment_id: str
    market: str | None
    metrics: Mapping[str, Any]
    summary: Mapping[str, Any]
    occurred_at: str = field(default_factory=_now)
    created_by: str = "ResearchKnowledgeEngine"

    @classmethod
    def new(cls, **values: Any) -> "KnowledgeFact":
        values.setdefault("fact_id", str(uuid4()))
        values["metrics"] = _frozen(values.get("metrics"))
        values["summary"] = _frozen(values.get("summary"))
        return cls(**values)


@dataclass(frozen=True)
class KnowledgeReport:
    report_id: str
    report_type: str
    scope: str
    scope_key: str
    fingerprint: str
    payload: Mapping[str, Any]
    generated_at: str = field(default_factory=_now)
    created_by: str = "ResearchKnowledgeEngine"

    @classmethod
    def new(cls, **values: Any) -> "KnowledgeReport":
        values.setdefault("report_id", str(uuid4()))
        values["payload"] = _frozen(values.get("payload"))
        return cls(**values)
