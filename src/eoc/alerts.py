"""Alert lifecycle implemented as immutable observations."""

from __future__ import annotations

from .models import Alert, AlertSeverity


class AlertManager:
    """Creates deduplicated operational alerts; never invokes CQRP business actions."""

    def __init__(self, repository, logger, notification_router=None) -> None:
        self.repository = repository
        self.logger = logger
        self.notification_router = notification_router

    def raise_alert(self, *, category: str, severity: AlertSeverity | str, component: str,
                    message: str, deduplication_key: str, details: dict | None = None,
                    correlation_id: str | None = None) -> Alert:
        alert = Alert.new(category=category, severity=severity, component=component,
                          message=message, deduplication_key=deduplication_key,
                          details=details, correlation_id=correlation_id)
        stored, created = self.repository.append_or_get(alert)
        self.logger.info({"event": "eoc_alert_raised", "alert_id": stored.alert_id,
                          "created": created, "severity": stored.severity.value,
                          "correlation_id": correlation_id})
        if created and self.notification_router:
            self.notification_router.route(stored)
        return stored
