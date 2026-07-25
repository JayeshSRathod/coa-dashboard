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
from src.persistence.signal_repository import SignalRepository
from src.persistence.trade_event_repository import TradeEventRepository
from src.persistence.trade_repository import TradeRepository
from src.persistence.validation_repository import ValidationRepository
from src.research.coa_pipeline import COAResearchPipeline
from src.research.collector import SnapshotCaptureService
from src.research.validation_pipeline import ValidationResearchPipeline
from src.research.signal_pipeline import SignalResearchPipeline
from src.signal.engine import SignalEngine
from src.signal.models import ResearchSignal
from src.execution.engine import PaperExecutionEngine
from src.execution.projector import project_trade
from src.research.paper_trading_pipeline import PaperTradingPipeline
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult


@dataclass(frozen=True)
class FyersResearchOutcome:
    snapshot_id: str | None
    coa_result: COAResearchResult | None
    validation_result: ValidationResult | None
    signal: ResearchSignal | None
    paper_trade_id: str | None
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
        self.signals = SignalRepository(self.connection)
        self.trades = TradeRepository(self.connection)
        self.trade_events = TradeEventRepository(self.connection)
        self.capture = SnapshotCaptureService(self.snapshots)
        self.coa = COAResearchPipeline(self.snapshots, self.coa_results, FrozenCOAAdapter())
        self.validation = ValidationResearchPipeline(
            self.snapshots, self.coa_results, self.validations, ValidationEngine()
        )
        self.signal = SignalResearchPipeline(
            self.snapshots, self.coa_results, self.validations, self.signals, SignalEngine()
        )
        self.paper = PaperTradingPipeline(
            self.signals, self.snapshots, self.trades, self.trade_events, PaperExecutionEngine()
        )

    def process(self, snapshot: OptionChainSnapshot) -> FyersResearchOutcome:
        """Persist one valid observation and produce deterministic research evidence.

        This method never creates an order, signal, or paper trade.
        """
        try:
            self.market_data.append_snapshot(snapshot)
            captured = self.capture.capture_payload(self._payload(snapshot), snapshot.instrument_id)
            if not captured.stored or not captured.snapshot_id:
                return FyersResearchOutcome(None, None, None, None, None, captured.error or "snapshot was not stored")
            coa = self.coa.process_snapshot_id(captured.snapshot_id)
            if not coa.success or coa.result is None:
                return FyersResearchOutcome(captured.snapshot_id, None, None, None, None, coa.error or "COA analysis failed")
            validation = self.validation.process_coa_result_id(coa.result.coa_result_id)
            if not validation.success or validation.result is None:
                return FyersResearchOutcome(captured.snapshot_id, coa.result, None, None, None, validation.error or "validation failed")
            signal = self.signal.process_validation_id(validation.result.validation_id)
            if not signal.success:
                return FyersResearchOutcome(captured.snapshot_id, coa.result, validation.result, None, None, signal.error or "signal generation failed")
            paper_trade_id = self._process_paper_signal(signal.signal, captured.snapshot_id)
            return FyersResearchOutcome(captured.snapshot_id, coa.result, validation.result, signal.signal, paper_trade_id)
        except Exception as exc:
            return FyersResearchOutcome(None, None, None, None, None, f"research processing failed: {type(exc).__name__}")

    def latest(self, instrument_id: str) -> FyersResearchOutcome | None:
        snapshot = self.snapshots.get_latest_snapshot(instrument_id)
        if snapshot is None:
            return None
        coa = next(iter(self.coa_results.list_by_snapshot(snapshot["snapshot_id"])), None)
        validation = (
            next(iter(self.validations.list_by_coa_result(coa.coa_result_id)), None)
            if coa is not None else None
        )
        signal = next(iter(self.signals.get_snapshot_signal(snapshot["snapshot_id"])), None)
        return FyersResearchOutcome(snapshot["snapshot_id"], coa, validation, signal, self._paper_trade_id(signal))

    def latest_snapshot(self, instrument_id: str) -> dict[str, object] | None:
        return self.snapshots.get_latest_snapshot(instrument_id)

    def paper_states(self, session_id: str | None = None) -> list[dict[str, object]]:
        trades = self.trades.get_session_trades(session_id) if session_id else self._all_session_trades()
        return [{"trade_id": trade.trade_id, "instrument": trade.instrument, "direction": trade.direction,
                 "status": state.status, "quantity_remaining": state.quantity_remaining,
                 "realized_pnl": state.realized_pnl, "unrealized_pnl": state.unrealized_pnl,
                 "opened_at": state.opened_at, "closed_at": state.closed_at}
                for trade in trades for state in [project_trade(trade, self.trade_events.get_events(trade.trade_id))]]

    def _all_session_trades(self):
        rows = self.connection.execute("SELECT DISTINCT session_id FROM simulated_trades ORDER BY session_id").fetchall()
        return [trade for row in rows for trade in self.trades.get_session_trades(row["session_id"])]

    def _process_paper_signal(self, signal: ResearchSignal | None, snapshot_id: str) -> str | None:
        if signal is None:
            return None
        outcome = self.paper.create_from_signal(signal.signal_id)
        for trade in self.trades.get_session_trades(signal.session_id):
            self.paper.process_snapshot(trade.trade_id, snapshot_id)
        return outcome.trade_id

    def _paper_trade_id(self, signal: ResearchSignal | None) -> str | None:
        if signal is None:
            return None
        trade = self.trades.get_by_signal(signal.signal_id, PaperExecutionEngine().config.execution_version, None)
        return trade.trade_id if trade else None

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
