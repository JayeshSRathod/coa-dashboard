"""Safe, append-only research processing for an explicitly fetched FYERS snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import os
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
from src.persistence.portfolio_repository import PortfolioRepository
from src.persistence.risk_decision_repository import RiskDecisionRepository
from src.research.coa_pipeline import COAResearchPipeline
from src.research.collector import SnapshotCaptureService
from src.research.validation_pipeline import ValidationResearchPipeline
from src.research.signal_pipeline import SignalResearchPipeline
from src.signal.engine import SignalEngine
from src.signal.models import ResearchSignal
from src.execution.engine import PaperExecutionEngine
from src.execution.projector import project_trade
from src.research.paper_trading_pipeline import PaperTradingPipeline
from src.risk.engine import PortfolioRiskEngine
from src.risk.models import Portfolio, RiskDecision
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult
from src.analytics.models import CompletedTrade


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
        self.portfolios = PortfolioRepository(self.connection)
        self.risk_decisions = RiskDecisionRepository(self.connection)
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
        self.paper_portfolio_id = os.getenv("CQRP_PAPER_PORTFOLIO_ID", "CQRPDW-PAPER")
        self.portfolios.insert(Portfolio(
            self.paper_portfolio_id, "CQRPDW Paper", None,
            float(os.getenv("CQRP_PAPER_CAPITAL", "100000")),
        ))
        self.risk_engine = PortfolioRiskEngine()

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

    def instruments(self) -> list[str]:
        rows = self.connection.execute("SELECT DISTINCT instrument FROM market_snapshots ORDER BY instrument").fetchall()
        return [str(row["instrument"]) for row in rows]

    def spot_history(self, instrument_id: str, limit: int = 20) -> list[float]:
        rows = self.connection.execute("SELECT spot FROM market_snapshots WHERE instrument=? ORDER BY market_captured_at DESC LIMIT ?", (instrument_id, limit)).fetchall()
        return [float(row["spot"]) for row in reversed(rows)]

    def worker_events(self, limit: int = 10) -> list[dict[str, object]]:
        return list(reversed(self.snapshots.list_events("FYERS_UNIVERSE_CYCLE")[-limit:]))

    def paper_states(self, session_id: str | None = None) -> list[dict[str, object]]:
        trades = self.trades.get_session_trades(session_id) if session_id else self._all_session_trades()
        return [{"trade_id": trade.trade_id, "instrument": trade.instrument, "direction": trade.direction,
                 "status": state.status, "quantity_remaining": state.quantity_remaining,
                 "realized_pnl": state.realized_pnl, "unrealized_pnl": state.unrealized_pnl,
                 "opened_at": state.opened_at, "closed_at": state.closed_at,
                 "created_at": trade.created_at, "option_type": trade.option_type,
                 "strike": trade.strike, "entry": state.executed_entry or trade.intended_entry,
                 "stop_loss": state.stop_loss, "target_1": state.target_1,
                 "target_2": state.target_2, "exit_reason": state.exit_reason}
                for trade in trades for state in [project_trade(trade, self.trade_events.get_events(trade.trade_id))]]

    def paper_trade_detail(self, trade_id: str) -> dict[str, object] | None:
        """Return persisted PAPER-only lifecycle evidence for workstation display."""
        trade = self.trades.get(trade_id)
        if trade is None:
            return None
        events = self.trade_events.get_events(trade_id)
        state = project_trade(trade, events)
        return {
            "trade_id": trade.trade_id, "instrument": trade.instrument,
            "direction": trade.direction, "expiry": trade.expiry, "strike": trade.strike,
            "option_type": trade.option_type, "quantity": trade.quantity,
            "created_at": trade.created_at, "intended_entry": trade.intended_entry,
            "entry": state.executed_entry, "stop_loss": state.stop_loss,
            "target_1": state.target_1, "target_2": state.target_2,
            "trailing_reference": state.trailing_reference, "status": state.status,
            "quantity_remaining": state.quantity_remaining,
            "realized_pnl": state.realized_pnl, "unrealized_pnl": state.unrealized_pnl,
            "mfe": state.mfe, "mae": state.mae, "opened_at": state.opened_at,
            "closed_at": state.closed_at, "exit_reason": state.exit_reason,
            "events": [
                {"occurred_at": event.occurred_at, "event": event.event_type,
                 "details": dict(event.payload)} for event in events
            ],
        }

    def current_paper_trade(self) -> dict[str, object] | None:
        """Prefer an active trade; otherwise return the latest retained paper trade."""
        states = self.paper_states()
        active = [row for row in states if row["status"] in {"PENDING", "OPEN", "PARTIALLY_EXITED"}]
        candidates = active or states
        if not candidates:
            return None
        latest = max(candidates, key=lambda row: str(row.get("created_at") or ""))
        return self.paper_trade_detail(str(latest["trade_id"]))

    def completed_paper_trades(self) -> list[CompletedTrade]:
        """Adapt closed, event-sourced paper trades for deterministic analytics."""
        completed: list[CompletedTrade] = []
        for trade in self._all_session_trades():
            state = project_trade(trade, self.trade_events.get_events(trade.trade_id))
            if state.status != "CLOSED" or state.opened_at is None or state.closed_at is None:
                continue
            signal = self.signals.get_signal(trade.signal_id)
            completed.append(CompletedTrade(
                trade_id=trade.trade_id, session_id=trade.session_id,
                experiment_id=trade.experiment_id, strategy_version=trade.strategy_version,
                instrument=trade.instrument, expiry=trade.expiry, direction=trade.direction,
                scenario=signal.scenario if signal else None,
                confidence_band=signal.confidence_band if signal else None,
                confidence_score=signal.confidence_score if signal else None,
                quantity=trade.quantity, entry_price=state.executed_entry,
                exit_price=state.average_exit_price, opened_at=state.opened_at,
                closed_at=state.closed_at, realized_pnl=state.realized_pnl,
                mae=state.mae, mfe=state.mfe,
            ))
        return sorted(completed, key=lambda item: (item.closed_at, item.trade_id))

    def risk_decision_for_signal(self, signal: ResearchSignal | None) -> RiskDecision | None:
        if signal is None:
            return None
        return self.risk_decisions.get_for_signal(
            signal.signal_id, self.paper_portfolio_id,
            self.risk_engine.config.risk_version, signal.experiment_id,
        )

    def _all_session_trades(self):
        rows = self.connection.execute("SELECT DISTINCT session_id FROM simulated_trades ORDER BY session_id").fetchall()
        return [trade for row in rows for trade in self.trades.get_session_trades(row["session_id"])]

    def _process_paper_signal(self, signal: ResearchSignal | None, snapshot_id: str) -> str | None:
        if signal is None or signal.signal_type not in {"BUY", "SELL"}:
            return None
        risk = self._evaluate_paper_risk(signal)
        if risk.decision not in {"APPROVED", "REDUCED_SIZE"}:
            return None
        outcome = self.paper.create_from_signal(signal.signal_id)
        for trade in self.trades.get_session_trades(signal.session_id):
            self.paper.process_snapshot(trade.trade_id, snapshot_id)
        return outcome.trade_id

    def _evaluate_paper_risk(self, signal: ResearchSignal) -> RiskDecision:
        """Gate paper creation from current projected positions, never broker exposure."""
        existing = self.risk_decision_for_signal(signal)
        if existing is not None:
            return existing
        portfolio = self.portfolios.get(self.paper_portfolio_id)
        if portfolio is None:  # Defensive: the identity is created during initialization.
            raise RuntimeError("CQRPDW paper portfolio is unavailable")
        states = self.paper_states()
        open_states = [row for row in states if row["status"] in {"PENDING", "OPEN", "PARTIALLY_EXITED"}]
        invested = sum(float(row.get("entry") or 0) * int(row.get("quantity_remaining") or 0)
                       for row in open_states)
        realized = sum(float(row.get("realized_pnl") or 0) for row in states)
        decision = self.risk_engine.evaluate(
            signal, portfolio, invested=invested, open_positions=len(open_states), daily_pnl=realized,
            instrument_exposure=sum(
                float(row.get("entry") or 0) * int(row.get("quantity_remaining") or 0)
                for row in open_states if row.get("instrument") == signal.instrument
            ),
        )
        return self.risk_decisions.append(decision)

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
