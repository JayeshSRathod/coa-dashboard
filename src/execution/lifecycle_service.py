"""Application service for CQRP PAPER trade lifecycle projections.

Lifecycle state is derived from immutable simulated trades and their append-only
event streams. No broker call, order submission, or event mutation is possible
through this service.
"""

from __future__ import annotations

from typing import Any

from src.persistence.trade_event_repository import TradeEventRepository
from src.persistence.trade_repository import TradeRepository

from .lifecycle import PaperTradeLifecycleEngine, PaperTradeLifecycleSummary


class PaperTradeLifecycleService:
    """Read and summarize authoritative PAPER trade event streams."""

    def __init__(
        self,
        trades: TradeRepository,
        events: TradeEventRepository,
        engine: PaperTradeLifecycleEngine | None = None,
    ) -> None:
        self.trades = trades
        self.events = events
        self.engine = engine or PaperTradeLifecycleEngine()

    def summary(self, trade_id: str) -> PaperTradeLifecycleSummary | None:
        trade = self.trades.get(trade_id)
        if trade is None:
            return None
        return self.engine.summarize(trade, self.events.get_events(trade_id))

    def detail(self, trade_id: str) -> dict[str, Any] | None:
        trade = self.trades.get(trade_id)
        if trade is None:
            return None
        events = self.events.get_events(trade_id)
        summary = self.engine.summarize(trade, events)
        return {
            "trade": {
                "trade_id": trade.trade_id,
                "signal_id": trade.signal_id,
                "session_id": trade.session_id,
                "snapshot_id": trade.snapshot_id,
                "experiment_id": trade.experiment_id,
                "strategy_version": trade.strategy_version,
                "execution_version": trade.execution_version,
                "instrument": trade.instrument,
                "direction": trade.direction,
                "expiry": trade.expiry,
                "strike": trade.strike,
                "option_type": trade.option_type,
                "quantity": trade.quantity,
                "intended_entry": trade.intended_entry,
                "initial_stop_loss": trade.initial_stop_loss,
                "initial_target_1": trade.initial_target_1,
                "initial_target_2": trade.initial_target_2,
                "created_at": trade.created_at,
            },
            "summary": summary.as_dict(),
            "timeline": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at,
                    "source_snapshot_id": event.source_snapshot_id,
                    "payload": dict(event.payload),
                }
                for event in events
            ],
            "mode": "PAPER_ONLY",
        }

    def session(self, session_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for trade in self.trades.get_session_trades(session_id):
            summary = self.engine.summarize(trade, self.events.get_events(trade.trade_id))
            rows.append(summary.as_dict())
        return rows

    def experiment(self, experiment_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for trade in self.trades.get_experiment_trades(experiment_id):
            summary = self.engine.summarize(trade, self.events.get_events(trade.trade_id))
            rows.append(summary.as_dict())
        return rows
