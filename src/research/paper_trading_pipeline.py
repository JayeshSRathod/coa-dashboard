"""Orchestration for deterministic event-sourced paper-trade simulation."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from src.execution.engine import PaperExecutionEngine
from src.execution.projector import project_trade
from src.persistence.signal_repository import SignalRepository
from src.persistence.snapshot_repository import SnapshotRepository
from src.persistence.trade_event_repository import TradeEventRepository
from src.persistence.trade_repository import TradeRepository

from .observability import emit_snapshot_event


@dataclass(frozen=True)
class PaperTradingOutcome:
    trade_id: str | None
    success: bool
    event_count: int = 0
    error: str | None = None


class PaperTradingPipeline:
    """Creates and replays simulated trades without any live-execution capability."""

    def __init__(self, signals: SignalRepository, snapshots: SnapshotRepository,
                 trades: TradeRepository, events: TradeEventRepository,
                 engine: PaperExecutionEngine, logger: logging.Logger | None=None) -> None:
        self.signals,self.snapshots,self.trades,self.events,self.engine=signals,snapshots,trades,events,engine
        self.logger=logger or logging.getLogger("cqrp.paper_trading")

    def create_from_signal(self, signal_id: str, *, experiment_id: str|None=None)->PaperTradingOutcome:
        signal=self.signals.get_signal(signal_id)
        if signal is None:return PaperTradingOutcome(None,False,error="signal not found")
        snapshot=self.snapshots.get(signal.snapshot_id)
        if snapshot is None:return PaperTradingOutcome(None,False,error="signal snapshot not found")
        trade,generated=self.engine.create_trade(signal,snapshot,experiment_id=experiment_id)
        if trade is None:return PaperTradingOutcome(None,True,0)
        stored=self.trades.insert(trade)
        count=0
        for event in generated:
            self.events.append(event);count+=1
        emit_snapshot_event(self.logger,"paper_trade_created",trade_id=stored.trade_id,signal_id=signal_id,session_id=stored.session_id)
        return PaperTradingOutcome(stored.trade_id,True,count)

    def process_snapshot(self, trade_id: str, snapshot_id: str)->PaperTradingOutcome:
        trade=self.trades.get(trade_id);snapshot=self.snapshots.get(snapshot_id)
        if trade is None or snapshot is None:return PaperTradingOutcome(trade_id if trade else None,False,error="trade or snapshot not found")
        state=project_trade(trade,self.events.get_events(trade_id))
        generated=self.engine.process_snapshot(trade,state,snapshot)
        for event in generated:self.events.append(event)
        if generated:emit_snapshot_event(self.logger,"paper_trade_events_appended",trade_id=trade_id,snapshot_id=snapshot_id,event_count=len(generated))
        return PaperTradingOutcome(trade_id,True,len(generated))

    def replay_session(self, session_id: str)->list[PaperTradingOutcome]:
        outcomes=[]
        for trade in self.trades.get_session_trades(session_id):
            for snapshot in self.snapshots.list_by_session(session_id):
                outcomes.append(self.process_snapshot(trade.trade_id,snapshot["snapshot_id"]))
        return outcomes

    def close_session(self, session_id: str, last_snapshot_id: str)->list[PaperTradingOutcome]:
        snapshot=self.snapshots.get(last_snapshot_id)
        if snapshot is None:return [PaperTradingOutcome(None,False,error="last snapshot not found")]
        outcomes=[]
        for trade in self.trades.get_session_trades(session_id):
            state=project_trade(trade,self.events.get_events(trade.trade_id))
            generated=self.engine.force_close(trade,state,snapshot)
            for event in generated:self.events.append(event)
            outcomes.append(PaperTradingOutcome(trade.trade_id,True,len(generated)))
        return outcomes
