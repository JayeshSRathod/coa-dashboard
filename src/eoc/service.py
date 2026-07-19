"""Dashboard-facing EOC service APIs; all APIs are read-only toward CQRP engines."""

from __future__ import annotations

import hashlib
import json

from .models import AuditEvent, ConfigurationRecord, SchedulerRun


class EnterpriseOperationsCenter:
    """Coordinates operational repositories without invoking strategy or execution code."""

    def __init__(self, *, health_repository, alert_repository, audit_repository, scheduler_repository,
                 metrics_repository, notification_repository, configuration_repository,
                 diagnostics_repository, health_monitor, alert_manager, diagnostics_center) -> None:
        self.health = health_repository
        self.alerts = alert_repository
        self.audit = audit_repository
        self.scheduler = scheduler_repository
        self.metrics = metrics_repository
        self.notifications = notification_repository
        self.configurations = configuration_repository
        self.diagnostics = diagnostics_repository
        self.health_monitor = health_monitor
        self.alert_manager = alert_manager
        self.diagnostics_center = diagnostics_center

    def get_system_health(self) -> dict:
        return {"components": self.health.latest_by_component(),
                "summary": self.health.summary()}

    def get_alerts(self, *, severity: str | None = None, limit: int = 100) -> list[dict]:
        return self.alerts.list(severity=severity, limit=limit)

    def get_activity_timeline(self, *, limit: int = 200) -> list[dict]:
        return self.metrics.activity_timeline(limit=limit)

    def get_scheduler_status(self) -> list[dict]:
        return self.scheduler.latest_by_job()

    def get_audit_log(self, *, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        return self.audit.list(entity_type=entity_type, limit=limit)

    def get_configuration_history(self, *, configuration_name: str | None = None) -> list[dict]:
        return self.configurations.list(configuration_name=configuration_name)

    def run_diagnostics(self, correlation_id: str | None = None) -> list[dict]:
        return [dict(report.__dict__) for report in self.diagnostics_center.run(correlation_id)]

    def record_scheduler_observation(self, **values) -> SchedulerRun:
        return self.scheduler.append(SchedulerRun.new(**values))

    def record_audit_event(self, **values) -> AuditEvent:
        return self.audit.append(AuditEvent.new(**values))

    def record_configuration(self, *, configuration_name: str, version: str, values: dict,
                             actor: str, correlation_id: str | None = None) -> ConfigurationRecord:
        checksum = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"),
                                             default=str).encode()).hexdigest()
        return self.configurations.append(ConfigurationRecord.new(
            configuration_name=configuration_name, version=version, checksum=checksum,
            values=values, actor=actor, correlation_id=correlation_id,
        ))
