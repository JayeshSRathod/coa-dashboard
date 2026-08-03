"""Governed application service for CQRP shadow PAPER execution.

This service coordinates an already-persisted TradePlan, its latest validation,
the authoritative ResearchSignal, and a fresh market snapshot. It can create
and persist simulated trades and append lifecycle events, but it has no broker
adapter and no live-order authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.persistence.trade_event_repository import TradeEventRepository
from src.persistence.trade_repository import TradeRepository
from src.signal.models import ResearchSignal
from src.trade_planning.models import TradePlan

from .manager import ExecutionDecision, ExecutionManager
from .models import PaperTrade, TradeEvent


@dataclass(frozen=True)
class ShadowExecutionResult:
    decision: ExecutionDecision
    trade: PaperTrade | None
    events: tuple[TradeEvent, ...]
    persisted: bool
    mode: str = "SHADOW_PAPER_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": {
                "eligible": self.decision.eligible,
                "action": self.decision.action,
                "selected_plan": self.decision.selected_plan,
                "reasons": list(self.decision.reasons),
                "evidence": dict(self.decision.evidence),
            },
            "trade_id": self.trade.trade_id if self.trade else None,
            "event_ids": [event.event_id for event in self.events],
            "persisted": self.persisted,
            "mode": self.mode,
        }


class ShadowExecutionService:
    """Create idempotent simulated trades after all CQRP gates pass."""

    def __init__(
        self,
        trades: TradeRepository,
        events: TradeEventRepository,
        manager: ExecutionManager | None = None,
    ) -> None:
        self.trades = trades
        self.events = events
        self.manager = manager or ExecutionManager()

    def assess(
        self,
        plan: TradePlan,
        validation: Mapping[str, Any] | None,
    ) -> ExecutionDecision:
        return self.manager.assess(plan, validation)

    def execute(
        self,
        *,
        plan: TradePlan,
        validation: Mapping[str, Any] | None,
        signal: ResearchSignal,
        snapshot: Mapping[str, Any],
        experiment_id: str | None = None,
    ) -> ShadowExecutionResult:
        decision, trade, generated_events = self.manager.create_paper_trade(
            plan=plan,
            premarket_validation=validation,
            signal=signal,
            snapshot=snapshot,
            experiment_id=experiment_id,
        )
        if trade is None:
            return ShadowExecutionResult(
                decision=decision,
                trade=None,
                events=(),
                persisted=False,
            )

        persisted_trade = self.trades.insert(trade)
        persisted_events = tuple(self.events.append(event) for event in generated_events)
        return ShadowExecutionResult(
            decision=decision,
            trade=persisted_trade,
            events=persisted_events,
            persisted=True,
        )
