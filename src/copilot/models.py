"""Immutable domain records for the advisory-only Copilot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frozen(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    source: str
    entity_type: str
    entity_id: str
    summary: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, **values: Any) -> "EvidenceReference":
        values.setdefault("evidence_id", str(uuid4()))
        values["payload"] = _frozen(values.get("payload", {}))
        return cls(**values)


@dataclass(frozen=True)
class CopilotResponse:
    response_id: str
    session_id: str
    persona: str
    question: str
    answer: str
    evidence_ids: tuple[str, ...]
    confidence: float
    accepted: bool
    created_at: str = field(default_factory=_now)

    @classmethod
    def new(cls, **values: Any) -> "CopilotResponse":
        values.setdefault("response_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values["evidence_ids"] = tuple(values.get("evidence_ids", ()))
        return cls(**values)


PERSONAS = ("TRADER", "RISK", "RESEARCH", "PORTFOLIO", "MARKET", "OPERATIONS", "EXECUTIVE")
