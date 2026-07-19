"""Structured observability for the snapshot pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from threading import Lock
from typing import Any


@dataclass
class SnapshotMetrics:
    capture_attempts: int = 0
    snapshots_stored: int = 0
    validation_failures: int = 0
    feed_interruptions: int = 0
    degraded_snapshots: int = 0
    total_capture_latency_ms: float = 0.0
    total_persistence_latency_ms: float = 0.0

    def __post_init__(self) -> None:
        self._lock = Lock()

    def record_capture(self, capture_latency_ms: float) -> None:
        with self._lock:
            self.capture_attempts += 1
            self.total_capture_latency_ms += capture_latency_ms

    def record_stored(self, persistence_latency_ms: float, degraded: bool) -> None:
        with self._lock:
            self.snapshots_stored += 1
            self.total_persistence_latency_ms += persistence_latency_ms
            self.degraded_snapshots += int(degraded)

    def record_validation_failure(self) -> None:
        with self._lock:
            self.validation_failures += 1

    def record_feed_interruption(self) -> None:
        with self._lock:
            self.feed_interruptions += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            values = asdict(self)
        values.pop("_lock", None)
        values["average_capture_latency_ms"] = (
            values["total_capture_latency_ms"] / values["capture_attempts"]
            if values["capture_attempts"] else 0.0
        )
        values["average_persistence_latency_ms"] = (
            values["total_persistence_latency_ms"] / values["snapshots_stored"]
            if values["snapshots_stored"] else 0.0
        )
        return values


def emit_snapshot_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit JSON that log processors can parse without a framework dependency."""
    logger.info(json.dumps({"event": event, **fields}, default=str, sort_keys=True))
