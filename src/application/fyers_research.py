"""Safe, append-only research processing for an explicitly fetched FYERS snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.coa.adapter import FrozenCOAAdapter
from src.coa.models import COAResearchResult
from src.market.snapshot import MarketSnapshotPayload
from src.market_data.models import OptionChainSnapshot
from src.persistence import RESEARCH_MIGRATIONS, apply_migrations, connect
from src.persistence.coa_result_repository import COAResultRepository
from src.persistence.market_data_repository import MarketDataRepository
from src.persistence.snapshot_repository import SnapshotRepository
from src.persistence.validation_repository import ValidationRepository
from src.research.coa_pipeline import COAResearchPipeline
from src.research.collector import SnapshotCaptureService
from src.research.validation_pipeline import ValidationResearchPipeline
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult


@dataclass(frozen=True)
class FyersResearchOutcome:
    snapshot_id: str | None
    coa_result: COAResearchResult | None
    validation_result: ValidationResult | None
    error: str | None = None


class FyersResearchService:
    """Owns the data-only FYERS → snapshot → COA → validation research path."""

    def __init__(self, database_path: str | Path) -> None:
        self.connection = connect(database_path)
        apply_migrations(self.connection, RESEARCH_MIGRATIONS)
        self.market_data = MarketDataRepository(self.connection)
        self.snapshots = SnapshotRepository(self.connection)
        self.coa_results = COAResultRepository(self.connection)
        self.validations = ValidationRepository(self.connection)
        self.capture = SnapshotCaptureService(self.snapshots)
        self.coa = COAResearchPipeline(self.snapshots, self.coa_results, FrozenCOAAdapter())
        self.validation = ValidationResearchPipeline(
            self.snapshots, self.coa_results, self.validations, ValidationEngine()
        )

    def process(self, snapshot: OptionChainSnapshot) -> FyersResearchOutcome:
        """Persist one valid observation and produce deterministic research evidence.

        This method never creates an order, signal, or paper trade.
        """
        try:
            self.market_data.append_snapshot(snapshot)
            captured = self.capture.capture_payload(self._payload(snapshot), snapshot.instrument_id)
            if not captured.stored or not captured.snapshot_id:
                return FyersResearchOutcome(None, None, None, captured.error or "snapshot was not stored")
            coa = self.coa.process_snapshot_id(captured.snapshot_id)
            if not coa.success or coa.result is None:
                return FyersResearchOutcome(captured.snapshot_id, None, None, coa.error or "COA analysis failed")
            validation = self.validation.process_coa_result_id(coa.result.coa_result_id)
            if not validation.success or validation.result is None:
                return FyersResearchOutcome(captured.snapshot_id, coa.result, None, validation.error or "validation failed")
            return FyersResearchOutcome(captured.snapshot_id, coa.result, validation.result)
        except Exception as exc:
            return FyersResearchOutcome(None, None, None, f"research processing failed: {type(exc).__name__}")

    def latest(self, instrument_id: str) -> FyersResearchOutcome | None:
        snapshot = self.snapshots.get_latest_snapshot(instrument_id)
        if snapshot is None:
            return None
        coa = next(iter(self.coa_results.list_by_snapshot(snapshot["snapshot_id"])), None)
        validation = (
            next(iter(self.validations.list_by_coa_result(coa.coa_result_id)), None)
            if coa is not None else None
        )
        return FyersResearchOutcome(snapshot["snapshot_id"], coa, validation)

    @staticmethod
    def _payload(snapshot: OptionChainSnapshot) -> MarketSnapshotPayload:
        strikes = sorted({contract.strike for contract in snapshot.contracts})
        atm_strike = min(strikes, key=lambda strike: abs(strike - snapshot.spot)) if strikes else None
        return MarketSnapshotPayload(
            instrument=snapshot.instrument_id,
            spot=snapshot.spot,
            source=snapshot.provider,
            option_chain=snapshot.coa_rows(),
            market_captured_at=snapshot.captured_at,
            atm_strike=atm_strike,
            expiry=snapshot.expiry or None,
            source_latency_ms=round(snapshot.latency_ms) if snapshot.latency_ms is not None else None,
            metadata={
                "market_data_snapshot_id": snapshot.snapshot_id,
                "quality_state": snapshot.quality.value,
                "quality_reasons": list(snapshot.quality_reasons),
                "provider": snapshot.provider,
            },
        )
