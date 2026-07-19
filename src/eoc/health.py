"""Pure health aggregation for the observational EOC."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import HealthState, HealthStatus


def classify_health(*, response_time_ms: float | None, error_count: int,
                    heartbeat_age_seconds: float | None, queue_backlog: int | None,
                    warning_response_ms: float = 500.0, degraded_response_ms: float = 2000.0,
                    offline_after_seconds: float = 120.0) -> HealthState:
    """Classify a health observation without making any remediation decision."""
    if heartbeat_age_seconds is not None and heartbeat_age_seconds > offline_after_seconds:
        return HealthState.OFFLINE
    if error_count > 0:
        return HealthState.FAILED
    if response_time_ms is not None and response_time_ms >= degraded_response_ms:
        return HealthState.DEGRADED
    if ((response_time_ms is not None and response_time_ms >= warning_response_ms)
            or (queue_backlog is not None and queue_backlog > 0)):
        return HealthState.WARNING
    return HealthState.HEALTHY


class HealthMonitor:
    """Records component observations only; it has no control-plane permissions."""

    def __init__(self, repository, logger, *, warning_response_ms: float = 500.0,
                 degraded_response_ms: float = 2000.0, offline_after_seconds: float = 120.0) -> None:
        self.repository = repository
        self.logger = logger
        self.warning_response_ms = warning_response_ms
        self.degraded_response_ms = degraded_response_ms
        self.offline_after_seconds = offline_after_seconds

    def publish(self, *, component: str, version: str, response_time_ms: float | None = None,
                error_count: int = 0, queue_backlog: int | None = None,
                heartbeat_age_seconds: float | None = 0.0, uptime_seconds: float | None = None,
                average_processing_ms: float | None = None, details: dict | None = None,
                correlation_id: str | None = None) -> HealthStatus:
        status = classify_health(
            response_time_ms=response_time_ms, error_count=error_count,
            heartbeat_age_seconds=heartbeat_age_seconds, queue_backlog=queue_backlog,
            warning_response_ms=self.warning_response_ms,
            degraded_response_ms=self.degraded_response_ms,
            offline_after_seconds=self.offline_after_seconds,
        )
        heartbeat = datetime.now(timezone.utc).isoformat()
        observation = HealthStatus.new(
            component=component, status=status, version=version, uptime_seconds=uptime_seconds,
            last_heartbeat_at=heartbeat, error_count=error_count,
            average_processing_ms=average_processing_ms, response_time_ms=response_time_ms,
            queue_backlog=queue_backlog, details=details, correlation_id=correlation_id,
        )
        stored = self.repository.append(observation)
        self.logger.info({"event": "eoc_health_published", "component": component,
                          "status": status.value, "correlation_id": correlation_id})
        return stored
