"""Service interface that assembles analytics inputs solely through repositories."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

from src.execution.projector import project_trade
from src.persistence.analytics_repository import AnalyticsRepository
from src.persistence.performance_snapshot_repository import PerformanceSnapshotRepository
from src.persistence.report_repository import ReportRepository
from src.persistence.signal_repository import SignalRepository
from src.persistence.trade_event_repository import TradeEventRepository
from src.research.observability import emit_snapshot_event

from .engine import PerformanceAnalyticsEngine
from .models import AnalyticsReport, CompletedTrade, PerformanceSnapshot


@dataclass(frozen=True)
class AnalyticsOutcome:
    success: bool
    report: AnalyticsReport | None = None
    error: str | None = None


class AnalyticsService:
    """Repository-backed reporting service. It neither changes trades nor invokes execution."""

    def __init__(
        self,
        analytics_repository: AnalyticsRepository,
        trade_event_repository: TradeEventRepository,
        signal_repository: SignalRepository,
        report_repository: ReportRepository,
        performance_snapshot_repository: PerformanceSnapshotRepository,
        engine: PerformanceAnalyticsEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.analytics_repository = analytics_repository
        self.trade_event_repository = trade_event_repository
        self.signal_repository = signal_repository
        self.report_repository = report_repository
        self.performance_snapshot_repository = performance_snapshot_repository
        self.engine = engine or PerformanceAnalyticsEngine()
        self.logger = logger or logging.getLogger("cqrp.analytics")

    def completed_trades(self, **filters: str | None) -> list[CompletedTrade]:
        items: list[CompletedTrade] = []
        for trade in self.analytics_repository.list_trades(**filters):
            state = project_trade(trade, self.trade_event_repository.get_events(trade.trade_id))
            if state.status != "CLOSED" or state.opened_at is None or state.closed_at is None:
                continue
            signal = self.signal_repository.get_signal(trade.signal_id)
            items.append(
                CompletedTrade(
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
                )
            )
        return sorted(items, key=lambda item: (item.closed_at, item.trade_id))

    def generate(
        self, *, report_type: str = "PERFORMANCE", group_by: str | None = None,
        session_id: str | None = None, experiment_id: str | None = None,
        strategy_version: str | None = None,
    ) -> AnalyticsOutcome:
        scope = {"session_id": session_id, "experiment_id": experiment_id,
                 "strategy_version": strategy_version, "group_by": group_by}
        try:
            trades = self.completed_trades(
                session_id=session_id, experiment_id=experiment_id, strategy_version=strategy_version
            )
            emit_snapshot_event(self.logger, "analytics_started", report_type=report_type,
                                completed_trades=len(trades), scope=scope)
            report = self.engine.report(
                trades, report_type=report_type, scope=scope, group_by=group_by
            )
            stored = self.report_repository.append(report)
            for point in self.engine.equity_curve(trades):
                self.performance_snapshot_repository.append(
                    PerformanceSnapshot.new(
                        report_id=stored.report_id, observed_at=str(point["observed_at"]),
                        equity=float(point["equity"]), drawdown=float(point["drawdown"]),
                        pnl=float(point["pnl"]), session_id=session_id,
                        payload={"trade_id": point["trade_id"]},
                    )
                )
        except Exception as exc:
            emit_snapshot_event(self.logger, "analytics_failed", report_type=report_type, error=str(exc))
            return AnalyticsOutcome(False, error=str(exc))
        emit_snapshot_event(self.logger, "analytics_completed", report_id=stored.report_id,
                            report_type=stored.report_type, source_fingerprint=stored.source_fingerprint)
        return AnalyticsOutcome(True, report=stored)

    def strategy_comparison(self, **filters: str | None) -> AnalyticsOutcome:
        return self.generate(report_type="STRATEGY_COMPARISON", group_by="strategy_version", **filters)

    def scenario_analysis(self, **filters: str | None) -> AnalyticsOutcome:
        return self.generate(report_type="SCENARIO", group_by="scenario", **filters)

    def validation_analysis(self, **filters: str | None) -> AnalyticsOutcome:
        return self.generate(report_type="VALIDATION_CONFIDENCE", group_by="confidence_band", **filters)
