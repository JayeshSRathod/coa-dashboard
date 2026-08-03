"""Immutable statistics snapshots generated from CQRP evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StatisticsSnapshot:
    statistics_id: str
    scope_type: str
    scope_value: str
    evidence_count: int
    report: Mapping[str, Any]
    statistics_version: str
    created_at: str
    created_by: str = "StatisticsService"

    @classmethod
    def new(cls, **values: Any) -> "StatisticsSnapshot":
        values.setdefault("statistics_id", str(uuid4()))
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "StatisticsService")
        values.setdefault("statistics_version", "statistics-v1")
        values["scope_type"] = str(values["scope_type"]).upper()
        values["scope_value"] = str(values["scope_value"])
        values["report"] = MappingProxyType(dict(values.get("report", {})))
        if values["scope_type"] not in {"PORTFOLIO", "INSTRUMENT", "SCENARIO", "HORIZON", "PLAN", "EXPERIMENT"}:
            raise ValueError("unsupported statistics scope_type")
        if int(values["evidence_count"]) < 0:
            raise ValueError("evidence_count cannot be negative")
        values["evidence_count"] = int(values["evidence_count"])
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "statistics_id": self.statistics_id,
            "scope_type": self.scope_type,
            "scope_value": self.scope_value,
            "evidence_count": self.evidence_count,
            "report": dict(self.report),
            "statistics_version": self.statistics_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
