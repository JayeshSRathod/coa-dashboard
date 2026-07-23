"""Provider health tracking with a deterministic circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CircuitState, ProviderHealth, QualityState, utc_now


@dataclass
class ProviderHealthTracker:
    provider: str
    failure_threshold: int = 2
    _failures: int = 0
    _last_latency_ms: float | None = None
    _last_heartbeat_at: str | None = None

    def success(self, latency_ms: float | None) -> ProviderHealth:
        self._failures = 0
        self._last_latency_ms = latency_ms
        self._last_heartbeat_at = utc_now()
        return self.current()

    def failure(self, latency_ms: float | None = None) -> ProviderHealth:
        self._failures += 1
        self._last_latency_ms = latency_ms
        return self.current()

    def current(self) -> ProviderHealth:
        circuit = CircuitState.OPEN if self._failures >= self.failure_threshold else CircuitState.CLOSED
        availability = QualityState.OFFLINE if circuit is CircuitState.OPEN else (QualityState.WARNING if self._failures else QualityState.HEALTHY)
        return ProviderHealth(self.provider, utc_now(), availability, self._last_latency_ms, self._failures, self._last_heartbeat_at, circuit)
