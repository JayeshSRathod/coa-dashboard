"""Immutable Enterprise Operations Center domain records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frozen(values: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    OFFLINE = "OFFLINE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class HealthStatus:
    health_id: str
    component: str
    status: HealthState
    version: str
    observed_at: str = field(default_factory=_now)
    uptime_seconds: float | None = None
    last_heartbeat_at: str | None = None
    error_count: int = 0
    average_processing_ms: float | None = None
    response_time_ms: float | None = None
    queue_backlog: int | None = None
    details: Mapping[str, Any] = field(default_factory=_frozen)
    correlation_id: str | None = None

    @classmethod
    def new(cls, **values: Any) -> "HealthStatus":
        values.setdefault("health_id", str(uuid4()))
        values["status"] = HealthState(values["status"])
        values["details"] = _frozen(values.get("details"))
        return cls(**values)


@dataclass(frozen=True)
class Alert:
    alert_id: str
    category: str
    severity: AlertSeverity
    component: str
    message: str
    deduplication_key: str
    observed_at: str = field(default_factory=_now)
    correlation_id: str | None = None
    details: Mapping[str, Any] = field(default_factory=_frozen)

    @classmethod
    def new(cls, **values: Any) -> "Alert":
        values.setdefault("alert_id", str(uuid4()))
        values["severity"] = AlertSeverity(values["severity"])
        values["details"] = _frozen(values.get("details"))
        return cls(**values)


@dataclass(frozen=True)
class SchedulerRun:
    scheduler_event_id: str
    job_id: str
    status: str
    observed_at: str = field(default_factory=_now)
    last_run_at: str | None = None
    next_run_at: str | None = None
    duration_ms: float | None = None
    result: Mapping[str, Any] = field(default_factory=_frozen)
    correlation_id: str | None = None

    @classmethod
    def new(cls, **values: Any) -> "SchedulerRun":
        values.setdefault("scheduler_event_id", str(uuid4()))
        values["result"] = _frozen(values.get("result"))
        return cls(**values)


@dataclass(frozen=True)
class AuditEvent:
    audit_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    occurred_at: str = field(default_factory=_now)
    before: Mapping[str, Any] = field(default_factory=_frozen)
    after: Mapping[str, Any] = field(default_factory=_frozen)
    correlation_id: str | None = None

    @classmethod
    def new(cls, **values: Any) -> "AuditEvent":
        values.setdefault("audit_id", str(uuid4()))
        values["before"] = _frozen(values.get("before"))
        values["after"] = _frozen(values.get("after"))
        return cls(**values)


@dataclass(frozen=True)
class ConfigurationRecord:
    configuration_event_id: str
    configuration_name: str
    version: str
    checksum: str
    values: Mapping[str, Any]
    actor: str
    occurred_at: str = field(default_factory=_now)
    correlation_id: str | None = None

    @classmethod
    def new(cls, **values: Any) -> "ConfigurationRecord":
        values.setdefault("configuration_event_id", str(uuid4()))
        values["values"] = _frozen(values.get("values"))
        return cls(**values)


@dataclass(frozen=True)
class DiagnosticReport:
    diagnostic_id: str
    name: str
    status: str
    recommendation: str
    details: Mapping[str, Any]
    observed_at: str = field(default_factory=_now)
    correlation_id: str | None = None

    @classmethod
    def new(cls, **values: Any) -> "DiagnosticReport":
        values.setdefault("diagnostic_id", str(uuid4()))
        values["details"] = _frozen(values.get("details"))
        return cls(**values)
