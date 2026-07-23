"""Canonical snapshot orchestration and compatibility bridge to CQRP replay."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from src.market.snapshot import MarketSnapshotPayload
from src.persistence.market_data_repository import MarketDataRepository
from src.research.collector import CaptureResult, SnapshotCaptureService

from .contracts import OptionChainRequest
from .provider_router import MarketDataRouter
from .quality import MarketDataQualityEngine, QualityAssessment


@dataclass(frozen=True)
class MarketDataCycleResult:
    snapshot_id: str
    quality: QualityAssessment
    legacy_capture: CaptureResult | None
    decision_allowed: bool


class MarketDataSnapshotService:
    """The only write path from providers into CQRP research snapshots."""

    def __init__(self, router: MarketDataRouter, repository: MarketDataRepository, quality: MarketDataQualityEngine | None = None, replay_capture: SnapshotCaptureService | None = None) -> None:
        self.router, self.repository = router, repository
        self.quality = quality or MarketDataQualityEngine()
        self.replay_capture = replay_capture
        if self.router.health_sink is None:
            self.router.health_sink = repository.append_health

    def capture(self, request: OptionChainRequest) -> MarketDataCycleResult:
        snapshot = self.router.fetch_option_chain(request)
        assessment = self.quality.assess(snapshot)
        snapshot = replace(snapshot, quality=assessment.state, quality_reasons=assessment.reasons)
        self.repository.append_snapshot(snapshot)
        legacy_capture = None
        if assessment.decision_allowed and self.replay_capture is not None:
            legacy_capture = self.replay_capture.capture_payload(self._legacy_payload(snapshot))
        return MarketDataCycleResult(snapshot.snapshot_id, assessment, legacy_capture, assessment.decision_allowed)

    @staticmethod
    def _legacy_payload(snapshot) -> MarketSnapshotPayload:
        return MarketSnapshotPayload(
            instrument=snapshot.instrument_id, spot=snapshot.spot, source=snapshot.provider,
            option_chain=snapshot.coa_rows(), market_captured_at=snapshot.captured_at,
            futures_price=snapshot.futures_price, expiry=snapshot.expiry,
            source_latency_ms=int(snapshot.latency_ms) if snapshot.latency_ms is not None else None,
            metadata={"market_data_snapshot_id": snapshot.snapshot_id, "quality_state": snapshot.quality.value, "quality_reasons": list(snapshot.quality_reasons)},
        )

    def replay(self, instrument_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        """Read canonical snapshots in deterministic chronological order."""
        return self.repository.list_snapshots(instrument_id, start, end)
