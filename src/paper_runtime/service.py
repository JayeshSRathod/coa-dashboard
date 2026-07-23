"""Deterministic in-process PAPER runtime. No broker or OMS calls occur here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.execution.engine import PaperExecutionEngine
from src.execution.models import PaperTrade, TradeEvent, TradeState
from src.execution.projector import project_trade
from src.signal.models import ResearchSignal


@dataclass(frozen=True)
class PaperRuntimeStatus:
    active: bool
    mode: str
    open_trades: int


class PaperRuntimeService:
    """Coordinates simulated trades from approved research signals only."""

    def __init__(self, engine: PaperExecutionEngine | None = None) -> None:
        self.engine = engine or PaperExecutionEngine()
        self._active = False
        self._trades: dict[str, PaperTrade] = {}
        self._events: dict[str, list[TradeEvent]] = {}

    def start(self, mode: str) -> PaperRuntimeStatus:
        if mode.upper().strip() != "PAPER":
            raise ValueError("Paper runtime accepts PAPER mode only.")
        self._active = True
        return self.status()

    def stop(self) -> PaperRuntimeStatus:
        self._active = False
        return self.status()

    def status(self) -> PaperRuntimeStatus:
        open_trades = sum(1 for trade_id in self._trades if self.state(trade_id).status in {"PENDING", "OPEN", "PARTIALLY_EXITED"})
        return PaperRuntimeStatus(self._active, "PAPER", open_trades)

    def submit_signal(self, signal: ResearchSignal, snapshot: Mapping[str, Any]) -> PaperTrade | None:
        if not self._active:
            raise RuntimeError("Paper runtime is not active.")
        trade, events = self.engine.create_trade(signal, snapshot)
        if trade is None:
            return None
        self._trades.setdefault(trade.trade_id, trade)
        self._events.setdefault(trade.trade_id, []).extend(events)
        return trade

    def process_snapshot(self, snapshot: Mapping[str, Any]) -> tuple[TradeEvent, ...]:
        if not self._active:
            return ()
        emitted: list[TradeEvent] = []
        for trade_id, trade in tuple(self._trades.items()):
            events = self.engine.process_snapshot(trade, self.state(trade_id), snapshot)
            if events:
                self._events[trade_id].extend(events)
                emitted.extend(events)
        return tuple(emitted)

    def state(self, trade_id: str) -> TradeState:
        return project_trade(self._trades[trade_id], self._events[trade_id])

    def events(self, trade_id: str) -> tuple[TradeEvent, ...]:
        return tuple(self._events[trade_id])
