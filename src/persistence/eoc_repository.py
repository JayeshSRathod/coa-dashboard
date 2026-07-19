"""Repository abstractions for append-only Enterprise Operations Center records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from src.eoc.models import (Alert, AlertSeverity, AuditEvent, ConfigurationRecord,
                            DiagnosticReport, HealthState, HealthStatus, SchedulerRun)
from .repository import SQLiteRepository


def _normalise(value: Any) -> Any:
    """Convert immutable mappings to ordinary JSON-compatible containers."""
    if isinstance(value, Mapping):
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalise(item) for item in value]
    return value


def _json(value: Any) -> str:
    return json.dumps(_normalise(value), default=str, sort_keys=True, separators=(",", ":"))


def _mapping(value: str | None) -> dict:
    return json.loads(value or "{}")


class HealthRepository(SQLiteRepository):
    def append(self, observation: HealthStatus) -> HealthStatus:
        with self.connection:
            self.connection.execute(
                """INSERT INTO eoc_health_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (observation.health_id, observation.component, observation.status.value, observation.version,
                 observation.observed_at, observation.uptime_seconds, observation.last_heartbeat_at,
                 observation.error_count, observation.average_processing_ms, observation.response_time_ms,
                 observation.queue_backlog, _json(observation.details), observation.correlation_id, "EOC"),
            )
        return observation

    def latest_by_component(self) -> list[dict]:
        rows = self.connection.execute(
            """SELECT h.* FROM eoc_health_observations h
               INNER JOIN (SELECT component, MAX(observed_at) observed_at
                           FROM eoc_health_observations GROUP BY component) latest
               ON h.component=latest.component AND h.observed_at=latest.observed_at
               ORDER BY h.component"""
        ).fetchall()
        return [dict(row) | {"details": _mapping(row["details_json"])} for row in rows]

    def summary(self) -> dict:
        latest = self.latest_by_component()
        states = {state.value: 0 for state in HealthState}
        for item in latest:
            states[item["status"]] = states.get(item["status"], 0) + 1
        return {"components": len(latest), "states": states}


class AlertRepository(SQLiteRepository):
    def append_or_get(self, alert: Alert) -> tuple[Alert, bool]:
        row = self.connection.execute(
            "SELECT * FROM eoc_alerts WHERE deduplication_key=?", (alert.deduplication_key,)
        ).fetchone()
        if row:
            return self._decode(row), False
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (alert.alert_id, alert.category, alert.severity.value, alert.component, alert.message,
                 alert.deduplication_key, alert.observed_at, alert.correlation_id, _json(alert.details), "EOC"),
            )
        return alert, True

    def _decode(self, row) -> Alert:
        return Alert.new(alert_id=row["alert_id"], category=row["category"], severity=row["severity"],
                         component=row["component"], message=row["message"],
                         deduplication_key=row["deduplication_key"], observed_at=row["observed_at"],
                         correlation_id=row["correlation_id"], details=_mapping(row["details_json"]))

    def list(self, *, severity: str | None = None, limit: int = 100) -> list[dict]:
        query, params = "SELECT * FROM eoc_alerts", []
        if severity:
            query += " WHERE severity=?"; params.append(severity)
        query += " ORDER BY observed_at DESC, alert_id DESC LIMIT ?"; params.append(limit)
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) | {"details": _mapping(row["details_json"])} for row in rows]


class AuditRepository(SQLiteRepository):
    def append(self, event: AuditEvent) -> AuditEvent:
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.audit_id, event.actor, event.action, event.entity_type, event.entity_id,
                 event.occurred_at, _json(event.before), _json(event.after), event.correlation_id, "EOC"),
            )
        return event

    def list(self, *, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        query, params = "SELECT * FROM eoc_audit_events", []
        if entity_type:
            query += " WHERE entity_type=?"; params.append(entity_type)
        query += " ORDER BY occurred_at DESC, audit_id DESC LIMIT ?"; params.append(limit)
        return [dict(row) | {"before": _mapping(row["before_json"]), "after": _mapping(row["after_json"])}
                for row in self.connection.execute(query, params).fetchall()]


class SchedulerRepository(SQLiteRepository):
    def append(self, run: SchedulerRun) -> SchedulerRun:
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_scheduler_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run.scheduler_event_id, run.job_id, run.status, run.observed_at, run.last_run_at,
                 run.next_run_at, run.duration_ms, _json(run.result), run.correlation_id),
            )
        return run

    def latest_by_job(self) -> list[dict]:
        rows = self.connection.execute(
            """SELECT s.* FROM eoc_scheduler_observations s
               INNER JOIN (SELECT job_id, MAX(observed_at) observed_at
                           FROM eoc_scheduler_observations GROUP BY job_id) latest
               ON s.job_id=latest.job_id AND s.observed_at=latest.observed_at
               ORDER BY s.job_id"""
        ).fetchall()
        return [dict(row) | {"result": _mapping(row["result_json"])} for row in rows]


class MetricsRepository(SQLiteRepository):
    def append(self, *, component: str, metric_name: str, value: float, unit: str,
               observed_at: str | None = None, correlation_id: str | None = None,
               details: dict | None = None) -> str:
        metric_id = __import__("uuid").uuid4().hex
        observed_at = observed_at or datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (metric_id, component, metric_name, value, unit, observed_at,
                 correlation_id, _json(details or {})),
            )
        return metric_id

    def activity_timeline(self, *, limit: int = 200) -> list[dict]:
        queries = (
            """SELECT observed_at AS occurred_at, 'HEALTH' AS activity_type, component AS subject,
                      status AS detail, correlation_id FROM eoc_health_observations""",
            """SELECT observed_at AS occurred_at, 'ALERT' AS activity_type, component AS subject,
                      severity || ': ' || message AS detail, correlation_id FROM eoc_alerts""",
            """SELECT occurred_at, 'AUDIT' AS activity_type, entity_type || ':' || entity_id AS subject,
                      action AS detail, correlation_id FROM eoc_audit_events""",
            """SELECT observed_at AS occurred_at, 'SCHEDULER' AS activity_type, job_id AS subject,
                      status AS detail, correlation_id FROM eoc_scheduler_observations""",
            """SELECT observed_at AS occurred_at, 'DIAGNOSTIC' AS activity_type, name AS subject,
                      status || ': ' || recommendation AS detail, correlation_id FROM eoc_diagnostic_reports""",
        )
        sql = " SELECT * FROM (" + " UNION ALL ".join(queries) + ") ORDER BY occurred_at DESC LIMIT ?"
        return [dict(row) for row in self.connection.execute(sql, (limit,)).fetchall()]


class NotificationRepository(SQLiteRepository):
    def append(self, delivery: dict) -> dict:
        delivery_id = __import__("uuid").uuid4().hex
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_notification_deliveries VALUES (?, ?, ?, ?, ?, ?, ?)",
                (delivery_id, delivery["alert_id"], delivery["channel"], delivery["status"],
                 delivery.get("reason"), datetime.now(timezone.utc).isoformat(),
                 _json(delivery)),
            )
        return dict(delivery) | {"delivery_id": delivery_id}


class ConfigurationGovernanceRepository(SQLiteRepository):
    def append(self, record: ConfigurationRecord) -> ConfigurationRecord:
        row = self.connection.execute(
            """SELECT * FROM eoc_configuration_history
               WHERE configuration_name=? AND version=? AND checksum=?""",
            (record.configuration_name, record.version, record.checksum),
        ).fetchone()
        if row:
            return ConfigurationRecord.new(
                configuration_event_id=row["configuration_event_id"],
                configuration_name=row["configuration_name"], version=row["version"],
                checksum=row["checksum"], values=_mapping(row["values_json"]), actor=row["actor"],
                occurred_at=row["occurred_at"], correlation_id=row["correlation_id"],
            )
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_configuration_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record.configuration_event_id, record.configuration_name, record.version,
                 record.checksum, _json(record.values), record.actor, record.occurred_at,
                 record.correlation_id, "EOC"),
            )
        return record

    def list(self, *, configuration_name: str | None = None) -> list[dict]:
        query, params = "SELECT * FROM eoc_configuration_history", []
        if configuration_name:
            query += " WHERE configuration_name=?"; params.append(configuration_name)
        query += " ORDER BY occurred_at DESC, configuration_event_id DESC"
        return [dict(row) | {"values": _mapping(row["values_json"])}
                for row in self.connection.execute(query, params).fetchall()]


class DiagnosticsRepository(SQLiteRepository):
    def append(self, report: DiagnosticReport) -> DiagnosticReport:
        with self.connection:
            self.connection.execute(
                "INSERT INTO eoc_diagnostic_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (report.diagnostic_id, report.name, report.status, report.recommendation,
                 _json(report.details), report.observed_at, report.correlation_id, "EOC"),
            )
        return report

    def list(self, *, limit: int = 100) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM eoc_diagnostic_reports ORDER BY observed_at DESC, diagnostic_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) | {"details": _mapping(row["details_json"])} for row in rows]
