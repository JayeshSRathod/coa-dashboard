"""Provider-neutral, dashboard-independent market snapshot capture service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from threading import Event
from time import perf_counter
from typing import Any, Callable

from src.market.snapshot import MarketSnapshotPayload, MarketSnapshotProvider
from src.persistence.snapshot_repository import SnapshotRepository

from .models import CapturedSnapshot
from .observability import SnapshotMetrics, emit_snapshot_event
from .validation import SnapshotValidationResult, SnapshotValidator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise_timestamp(value: str | None) -> str:
    """Use UTC for replay ordering, leaving malformed provider values for validation."""
    if value is None:
        return _utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return value
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _session_id(instrument: str, market_captured_at: str) -> str:
    return f"{instrument}:{market_captured_at[:10]}"


@dataclass(frozen=True)
class CaptureResult:
    stored: bool
    snapshot_id: str | None
    validation: SnapshotValidationResult | None
    error: str | None = None


class SnapshotCaptureService:
    def __init__(
        self,
        repository: SnapshotRepository,
        validator: SnapshotValidator | None = None,
        metrics: SnapshotMetrics | None = None,
        logger: logging.Logger | None = None,
        after_store: Callable[[str], Any] | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator or SnapshotValidator()
        self.metrics = metrics or SnapshotMetrics()
        self.logger = logger or logging.getLogger("cqrp.snapshot_capture")
        self.after_store = after_store

    def capture_payload(
        self,
        payload: MarketSnapshotPayload,
        expected_instrument: str | None = None,
    ) -> CaptureResult:
        started = perf_counter()
        ingested_at = _utc_now()
        market_captured_at = _normalise_timestamp(payload.market_captured_at)
        snapshot = CapturedSnapshot.new(
            session_id=payload.session_id or _session_id(payload.instrument, market_captured_at),
            instrument=payload.instrument,
            spot=payload.spot,
            source=payload.source,
            market_captured_at=market_captured_at,
            ingested_at=ingested_at,
            option_chain=payload.option_chain,
            futures_price=payload.futures_price,
            atm_strike=payload.atm_strike,
            expiry=payload.expiry,
            expiry_type=payload.expiry_type,
            source_latency_ms=payload.source_latency_ms,
            coa_payload=payload.coa_payload,
            metadata=payload.metadata,
        )
        previous = self.repository.get_latest_snapshot(snapshot.instrument)
        validation = self.validator.validate(
            snapshot,
            previous_market_captured_at=previous["market_captured_at"] if previous else None,
            previous_session_id=previous["session_id"] if previous else None,
            previous_expiry=previous["expiry"] if previous else None,
            previous_expiry_type=previous["expiry_type"] if previous else None,
            expected_instrument=expected_instrument,
        )
        self.metrics.record_capture((perf_counter() - started) * 1000)

        if not validation.is_valid:
            self.metrics.record_validation_failure()
            self.repository.record_event(
                "snapshot_validation_failed",
                "WARNING",
                {"snapshot_id": snapshot.snapshot_id, "errors": validation.errors, "warnings": validation.warnings},
                snapshot.instrument,
            )
            emit_snapshot_event(
                self.logger, "snapshot_validation_failed", instrument=snapshot.instrument,
                snapshot_id=snapshot.snapshot_id, errors=validation.errors,
            )
            return CaptureResult(False, None, validation, "snapshot validation failed")

        persist_started = perf_counter()
        self.repository.append(snapshot, validation)
        if self.after_store is not None:
            try:
                self.after_store(snapshot.snapshot_id)
            except Exception as exc:
                # Capture remains durable; analysis failures are observable and recoverable.
                self.repository.record_event(
                    "snapshot_post_persist_processing_failed", "ERROR",
                    {"snapshot_id": snapshot.snapshot_id, "error": str(exc)}, snapshot.instrument,
                )
                emit_snapshot_event(
                    self.logger, "snapshot_post_persist_processing_failed",
                    snapshot_id=snapshot.snapshot_id, instrument=snapshot.instrument, error=str(exc),
                )
        persistence_latency_ms = (perf_counter() - persist_started) * 1000
        self.metrics.record_stored(persistence_latency_ms, degraded=not validation.is_complete)
        emit_snapshot_event(
            self.logger, "snapshot_stored", instrument=snapshot.instrument,
            snapshot_id=snapshot.snapshot_id, completeness=validation.data_completeness,
            capture_latency_ms=(perf_counter() - started) * 1000,
            persistence_latency_ms=persistence_latency_ms,
        )
        if not validation.is_complete:
            self.repository.record_event(
                "snapshot_degraded",
                "WARNING",
                {"snapshot_id": snapshot.snapshot_id, "warnings": validation.warnings,
                 "missing_strikes": validation.missing_strikes},
                snapshot.instrument,
            )
        return CaptureResult(True, snapshot.snapshot_id, validation)

    def capture_from_provider(
        self,
        provider: MarketSnapshotProvider,
        instrument: str,
    ) -> CaptureResult:
        try:
            payload = provider.fetch_snapshot(instrument)
        except Exception as exc:  # Provider failures must become observable events.
            self.metrics.record_feed_interruption()
            self.repository.record_event(
                "feed_interruption", "ERROR", {"error": str(exc), "source": type(provider).__name__}, instrument
            )
            emit_snapshot_event(self.logger, "feed_interruption", instrument=instrument, error=str(exc))
            return CaptureResult(False, None, None, str(exc))
        return self.capture_payload(payload, expected_instrument=instrument)


class SnapshotPollingService:
    """Long-running polling loop; lifecycle ownership remains outside the dashboard."""

    def __init__(
        self,
        capture_service: SnapshotCaptureService,
        provider: MarketSnapshotProvider,
        instrument: str,
        interval_seconds: float,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("snapshot interval must be positive")
        self.capture_service = capture_service
        self.provider = provider
        self.instrument = instrument
        self.interval_seconds = interval_seconds

    def run_until(self, stop_event: Event, max_cycles: int | None = None) -> list[CaptureResult]:
        results: list[CaptureResult] = []
        while not stop_event.is_set() and (max_cycles is None or len(results) < max_cycles):
            results.append(self.capture_service.capture_from_provider(self.provider, self.instrument))
            stop_event.wait(self.interval_seconds)
        return results
