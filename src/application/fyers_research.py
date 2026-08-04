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
from src.persistence.structure_event_repository import StructureEventRepository
from src.persistence.trade_plan_repository import TradePlanRepository
from src.persistence.premarket_validation_repository import PreMarketValidationRepository
from src.persistence.scenario_track_repository import ScenarioTrackRepository
from src.research.coa_pipeline import COAResearchPipeline
from src.research.collector import SnapshotCaptureService
from src.research.validation_pipeline import ValidationResearchPipeline
from src.research.signal_pipeline import SignalResearchPipeline
from src.research.dynamic_structure import DynamicStructureEngine
from src.research.capture_profile import capture_metadata
from src.research.market_timing import is_preclose_window
from src.research.scenario_shadow import ScenarioShadowEngine
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
from src.trade_planning.service import TradePlanningService
from src.premarket_validation.models import PreMarketObservation, PreMarketValidationResult
from src.premarket_validation.service import PreMarketValidationService


@dataclass(frozen=True)
class FyersResearchOutcome:
    snapshot_id: str | None
    coa_result: COAResearchResult | None
    validation_result: ValidationResult | None
    signal: ResearchSignal | None
    paper_trade_id: str | None
    trade_plan_id: str | None = None
    premarket_validation_id: str | None = None
    scenario_track_id: str | None = None
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
        self.structure_events = StructureEventRepository(self.connection)
        self.trade_plans = TradePlanRepository(self.connection)
        self.premarket_validations = PreMarketValidationRepository(self.connection)
        self.scenario_tracks = ScenarioTrackRepository(self.connection)
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
        self.dynamic_structure = DynamicStructureEngine(self.structure_events)
        self.scenario_shadow = ScenarioShadowEngine()
        # These services are deliberately downstream of the persisted FYERS
        # snapshot path.  They never fetch market data and never submit orders.
        self.trade_planning = TradePlanningService(self, self.trade_plans)
        self.premarket_validation = PreMarketValidationService(self.premarket_validations)

    def close(self) -> None:
        """Close this service's SQLite connection after a dashboard render."""
        self.connection.close()

    def process(self, snapshot: OptionChainSnapshot) -> FyersResearchOutcome:
        """Persist one valid observation and produce deterministic research evidence.

        This method never creates an order, signal, or paper trade.
        """
        try:
            self.market_data.append_snapshot(snapshot)
            captured = self.capture.capture_payload(self._payload(snapshot), snapshot.instrument_id)
            if not captured.stored or not captured.snapshot_id:
                return FyersResearchOutcome(
                    None, None, None, None, None,
                    error=captured.error or "snapshot was not stored",
                )
            coa = self.coa.process_snapshot_id(captured.snapshot_id)
            if not coa.success or coa.result is None:
                return FyersResearchOutcome(
                    captured.snapshot_id, None, None, None, None,
                    error=coa.error or "COA analysis failed",
                )
            scenario_track_id = self._record_scenario_track(captured.snapshot_id, coa.result)
            validation = self.validation.process_coa_result_id(coa.result.coa_result_id)
            if not validation.success or validation.result is None:
                return FyersResearchOutcome(
                    captured.snapshot_id, coa.result, None, None, None,
                    error=validation.error or "validation failed",
                )
            premarket_validation_id = self._revalidate_opening_plan(
                captured.snapshot_id, coa.result, validation.result
            )
            signal = self.signal.process_validation_id(validation.result.validation_id)
            if not signal.success:
                return FyersResearchOutcome(
                    captured.snapshot_id, coa.result, validation.result, None, None,
                    premarket_validation_id=premarket_validation_id,
                    error=signal.error or "signal generation failed",
                )
            paper_trade_id = self._process_paper_signal(signal.signal, captured.snapshot_id)
            self._record_dynamic_structure(captured.snapshot_id, coa.result, validation.result, signal.signal, paper_trade_id)
            plan = self._create_preclose_plan(captured.snapshot_id, snapshot.instrument_id)
            if plan is not None:
                self.snapshots.record_event(
                    "preclose_trade_plan_created", "INFO",
                    {"snapshot_id": captured.snapshot_id, "trade_plan_id": plan.trade_plan_id,
                     "readiness": plan.readiness, "planning_horizon": plan.planning_horizon,
                     "execution_mode": "PAPER_ONLY", "capture_window": "15:00-15:20_IST"},
                    snapshot.instrument_id,
                )
            return FyersResearchOutcome(
                captured.snapshot_id, coa.result, validation.result, signal.signal, paper_trade_id,
                trade_plan_id=plan.trade_plan_id if plan else None,
                premarket_validation_id=premarket_validation_id,
                scenario_track_id=scenario_track_id,
            )
        except Exception as exc:
            return FyersResearchOutcome(
                None, None, None, None, None,
                error=f"research processing failed: {type(exc).__name__}",
            )

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

    def latest_scenario_track(self, instrument_id: str) -> dict[str, object] | None:
        """Return the latest observational combined COA 1--18 track."""
        return self.scenario_tracks.latest(instrument_id)

    def backfill_scenario_tracks(self, instrument_id: str) -> int:
        """Replay combined scenario observations without changing prior evidence."""
        processed = 0
        histories: dict[str, list[dict[str, object]]] = {}
        for snapshot in self.snapshots.list_by_instrument(instrument_id):
            coa = next(iter(self.coa_results.list_by_snapshot(snapshot["snapshot_id"])), None)
            if coa is None:
                continue
            session_id = str(snapshot["session_id"])
            history = histories.setdefault(session_id, [])
            history.append(snapshot)
            self._append_scenario_track(snapshot, coa, history)
            processed += 1
        return processed

    def latest_trade_plan(self, instrument_id: str) -> dict[str, object] | None:
        """Return an advisory persisted plan; it has no execution authority."""
        return self.trade_plans.latest(instrument_id)

    def trade_plan_history(self, instrument_id: str, limit: int = 100) -> list[dict[str, object]]:
        return self.trade_plans.list(instrument=instrument_id, limit=limit)

    def _record_scenario_track(self, snapshot_id: str, coa_result: COAResearchResult) -> str:
        snapshot = self.snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id} was not found")
        history = self.snapshots.list_by_session(str(snapshot["session_id"]))
        return self._append_scenario_track(snapshot, coa_result, history)

    def _append_scenario_track(self, snapshot: dict[str, object], coa_result: COAResearchResult,
                               history: list[dict[str, object]]) -> str:
        snapshot_id = str(snapshot["snapshot_id"])
        existing = self.scenario_tracks.get_for_snapshot(snapshot_id, self.scenario_shadow.version)
        if existing is not None:
            return str(existing["scenario_track_id"])
        record = self.scenario_shadow.evaluate(snapshot, coa_result, history)
        track_id = self.scenario_tracks.append(record)
        self.snapshots.record_event(
            "coa_combined_scenario_recorded", "INFO",
            {"snapshot_id": snapshot_id, "scenario_track_id": track_id,
             "structural_scenario": record["structural_scenario_number"],
             "tactical_scenario": record["tactical_scenario_number"],
             "catalog_version": record["catalog_version"], "observation_only": True},
            str(snapshot["instrument"]),
        )
        return track_id

    def _create_preclose_plan(self, snapshot_id: str, instrument_id: str):
        """Create tomorrow-plan evidence only from the 15:00--15:20 IST window."""
        snapshot = self.snapshots.get(snapshot_id)
        if snapshot is None or not is_preclose_window(str(snapshot["market_captured_at"])):
            return None
        return self.trade_planning.create_latest(instrument_id)

    def latest_premarket_validation(self, trade_plan_id: str) -> dict[str, object] | None:
        return self.premarket_validations.latest_for_plan(trade_plan_id)

    def instruments(self) -> list[str]:
        rows = self.connection.execute("SELECT DISTINCT instrument FROM market_snapshots ORDER BY instrument").fetchall()
        return [str(row["instrument"]) for row in rows]

    def spot_history(self, instrument_id: str, limit: int = 20) -> list[float]:
        rows = self.connection.execute("SELECT spot FROM market_snapshots WHERE instrument=? ORDER BY market_captured_at DESC LIMIT ?", (instrument_id, limit)).fetchall()
        return [float(row["spot"]) for row in reversed(rows)]

    def worker_events(self, limit: int = 10) -> list[dict[str, object]]:
        return list(reversed(self.snapshots.list_events("FYERS_UNIVERSE_CYCLE")[-limit:]))

    def system_events(self, limit: int = 50) -> list[dict[str, object]]:
        """Expose persisted operational evidence without dashboard SQL access."""
        return list(reversed(self.snapshots.list_events()[-limit:]))

    def market_health(self) -> list[dict[str, object]]:
        """Return the latest persisted provider-health observations."""
        return self.market_data.latest_health()

    def dynamic_events(self, instrument_id: str, *, session_id: str | None = None,
                       event_types: tuple[str, ...] = (), limit: int = 10_000) -> list[dict[str, object]]:
        """Read-only dynamic CE/PE wall and level-event history for research UI."""
        return self.structure_events.list_events(instrument_id, session_id=session_id,
                                                 event_types=event_types, limit=limit)

    def dynamic_walls(self, instrument_id: str, *, session_id: str | None = None,
                      limit: int = 25_000) -> list[dict[str, object]]:
        return self.structure_events.list_walls(instrument_id, session_id=session_id, limit=limit)

    def dynamic_sessions(self, instrument_id: str) -> list[str]:
        return self.structure_events.list_sessions(instrument_id)

    def dynamic_event_types(self, instrument_id: str, session_id: str | None = None) -> list[str]:
        return self.structure_events.list_event_types(instrument_id, session_id)

    def backfill_dynamic_structure(self, instrument_id: str) -> int:
        """Replay existing captured research evidence without changing any decision.

        Duplicate protection in the append-only repository makes this safe to
        rerun after an interrupted replay.
        """
        processed = 0
        for snapshot in self.snapshots.list_by_instrument(instrument_id):
            coa = next(iter(self.coa_results.list_by_snapshot(snapshot["snapshot_id"])), None)
            if coa is None:
                continue
            validation = next(iter(self.validations.list_by_coa_result(coa.coa_result_id)), None)
            signal = next(iter(self.signals.get_snapshot_signal(snapshot["snapshot_id"])), None)
            self._record_dynamic_structure(
                snapshot["snapshot_id"], coa, validation, signal, self._paper_trade_id(signal)
            )
            processed += 1
        return processed

    def _record_dynamic_structure(self, snapshot_id: str, coa_result: COAResearchResult,
                                  validation_result: ValidationResult, signal: ResearchSignal | None,
                                  paper_trade_id: str | None) -> None:
        snapshot = self.snapshots.get(snapshot_id)
        if snapshot is None:
            return
        risk = self.risk_decision_for_signal(signal)
        try:
            self.dynamic_structure.process(snapshot, coa_result=coa_result,
                                           validation_result=validation_result, signal=signal,
                                           risk_decision=risk, paper_trade_id=paper_trade_id)
        except Exception as exc:
            self.snapshots.record_event("dynamic_structure_processing_failed", "ERROR",
                                        {"snapshot_id": snapshot_id, "error": str(exc)}, snapshot.get("instrument"))

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

    def current_paper_trade(self, *, instrument: str | None = None) -> dict[str, object] | None:
        """Prefer an active trade; otherwise return the latest retained paper trade."""
        states = self.paper_states()
        if instrument:
            states = [row for row in states if row.get("instrument") == instrument]
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

    def _revalidate_opening_plan(
        self,
        snapshot_id: str,
        coa_result: COAResearchResult,
        validation_result: ValidationResult,
    ) -> str | None:
        """Validate only the first persisted snapshot of a new session.

        The previous plan is treated as immutable evidence.  This hook is
        intentionally read-only with respect to paper execution: it records a
        pre-market decision but cannot create, modify, or submit a trade.
        """
        snapshot = self.snapshots.get(snapshot_id)
        if snapshot is None:
            return None
        session_rows = self.snapshots.list_by_session(str(snapshot["session_id"]))
        if len(session_rows) != 1:
            return None

        prior = self.trade_plans.latest(str(snapshot["instrument"]))
        if prior is None or prior.get("snapshot_id") == snapshot_id:
            return None
        source_snapshot = self.snapshots.get(str(prior["snapshot_id"]))
        if source_snapshot is None or source_snapshot.get("session_id") == snapshot.get("session_id"):
            return None

        plan = PreMarketValidationService.plan_from_record(prior)
        source_risk = (
            self.risk_decisions.get(str(plan.risk_decision_id))
            if plan.risk_decision_id else None
        )
        technical = dict(coa_result.raw_output.get("technical_confirmation") or
                         coa_result.raw_output.get("technical") or {})
        observation = PreMarketObservation(
            trade_plan_id=plan.trade_plan_id,
            snapshot_id=snapshot_id,
            observed_at=str(snapshot.get("market_captured_at") or snapshot.get("captured_at")),
            instrument=str(snapshot["instrument"]),
            planning_horizon=plan.planning_horizon,
            previous_close=float(source_snapshot["spot"]),
            observed_spot=float(snapshot["spot"]),
            coa_bias=self._coa_bias(coa_result),
            technical_status=self._mapping_value(technical, "status", "state"),
            technical_bias=self._mapping_value(technical, "bias", "direction"),
            momentum_state=self._mapping_value(coa_result.momentum, "state", "classification", "bias"),
            risk_status=source_risk.decision if source_risk is not None else "REJECTED",
            data_quality="PASS" if snapshot.get("data_quality_status") == "VALID" else "FAILED",
            metadata={
                "source_session_id": source_snapshot.get("session_id"),
                "observed_session_id": snapshot.get("session_id"),
                "coa_result_id": coa_result.coa_result_id,
                "validation_id": validation_result.validation_id,
                "validation_score": validation_result.overall_score,
                "execution_mode": "PAPER_ONLY",
            },
        )
        result = self.premarket_validation.validate(plan, observation)
        self.snapshots.record_event(
            "premarket_plan_revalidated", "INFO",
            {"trade_plan_id": plan.trade_plan_id, "validation_id": result.validation_id,
             "result": result.validation_result, "selected_plan": result.selected_plan,
             "execution_mode": "PAPER_ONLY"},
            str(snapshot["instrument"]),
        )
        return result.validation_id

    @staticmethod
    def _coa_bias(coa_result: COAResearchResult) -> str:
        direction = str(coa_result.direction or coa_result.trend or "").upper()
        if direction in {"BUY", "BULLISH", "UP"}:
            return "BULLISH"
        if direction in {"SELL", "BEARISH", "DOWN"}:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _mapping_value(source: object, *keys: str) -> str | None:
        if source is None:
            return None
        if hasattr(source, "get"):
            for key in keys:
                value = source.get(key)  # type: ignore[union-attr]
                if value is not None:
                    return str(value)
        for key in keys:
            value = getattr(source, key, None)
            if value is not None:
                return str(value)
        return None

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
        provider_metadata = dict(snapshot.metadata)
        capture_profile = str(provider_metadata.get("capture_profile") or "research_core_v1")
        capture_evidence = capture_metadata(
            profile=capture_profile,
            provider_symbol=provider_metadata.get("provider_symbol"),
            requested_expiry=provider_metadata.get("requested_expiry"),
            resolved_expiry=snapshot.expiry or None,
            spot=snapshot.spot,
            atm_strike=atm_strike,
            strikes=strikes,
            strike_count=len(strikes),
        )
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
                "capture": capture_evidence,
                "provider_metadata": provider_metadata,
            },
        )
