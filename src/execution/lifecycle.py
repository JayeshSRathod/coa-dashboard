"""Deterministic lifecycle analytics for event-sourced CQRP PAPER trades.

This module derives an immutable summary from the existing PaperTrade and
TradeEvent stream. It does not mutate trades, place orders, or call a broker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .models import PaperTrade, TradeEvent
from .projector import project_trade


@dataclass(frozen=True)
class PaperTradeLifecycleSummary:
    trade_id: str
    stage: str
    status: str
    entry_price: float | None
    average_exit_price: float | None
    quantity: int
    quantity_remaining: int
    realized_pnl: float
    unrealized_pnl: float
    mfe: float
    mae: float
    initial_risk_per_unit: float | None
    realized_r_multiple: float | None
    holding_seconds: float | None
    exit_reason: str | None
    event_count: int
    milestones: tuple[str, ...]
    metrics: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "stage": self.stage,
            "status": self.status,
            "entry_price": self.entry_price,
            "average_exit_price": self.average_exit_price,
            "quantity": self.quantity,
            "quantity_remaining": self.quantity_remaining,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "mfe": self.mfe,
            "mae": self.mae,
            "initial_risk_per_unit": self.initial_risk_per_unit,
            "realized_r_multiple": self.realized_r_multiple,
            "holding_seconds": self.holding_seconds,
            "exit_reason": self.exit_reason,
            "event_count": self.event_count,
            "milestones": list(self.milestones),
            "metrics": dict(self.metrics),
        }


class PaperTradeLifecycleEngine:
    """Build a lifecycle summary from the authoritative append-only event stream."""

    version = "paper-lifecycle-v1"

    def summarize(
        self,
        trade: PaperTrade,
        events: Iterable[TradeEvent],
    ) -> PaperTradeLifecycleSummary:
        ordered = tuple(sorted(events, key=lambda item: (item.occurred_at, item.event_id)))
        state = project_trade(trade, ordered)
        event_types = tuple(item.event_type for item in ordered)
        stage = self._stage(state.status, event_types)
        milestones = self._milestones(event_types)
        initial_risk = self._initial_risk_per_unit(trade)
        realized_r = self._realized_r_multiple(state.realized_pnl, initial_risk, trade.quantity)
        holding = self._holding_seconds(state.opened_at, state.closed_at)
        metrics = MappingProxyType({
            "execution_version": trade.execution_version,
            "strategy_version": trade.strategy_version,
            "experiment_id": trade.experiment_id,
            "entry_fill_count": event_types.count("ENTRY_FILLED"),
            "partial_exit_count": event_types.count("PARTIAL_EXIT"),
            "stop_move_count": event_types.count("STOP_LOSS_MOVED"),
            "mark_count": event_types.count("MARK_OBSERVED"),
            "target_1_hit": "TARGET_1_HIT" in event_types,
            "target_2_hit": "TARGET_2_HIT" in event_types,
            "trailing_activated": "TRAILING_UPDATED" in event_types,
            "paper_only": True,
            "lifecycle_version": self.version,
        })
        return PaperTradeLifecycleSummary(
            trade_id=trade.trade_id,
            stage=stage,
            status=state.status,
            entry_price=state.executed_entry,
            average_exit_price=state.average_exit_price,
            quantity=trade.quantity,
            quantity_remaining=state.quantity_remaining,
            realized_pnl=round(float(state.realized_pnl), 6),
            unrealized_pnl=round(float(state.unrealized_pnl), 6),
            mfe=round(float(state.mfe), 6),
            mae=round(float(state.mae), 6),
            initial_risk_per_unit=initial_risk,
            realized_r_multiple=realized_r,
            holding_seconds=holding,
            exit_reason=state.exit_reason,
            event_count=len(ordered),
            milestones=milestones,
            metrics=metrics,
        )

    @staticmethod
    def _stage(status: str, event_types: tuple[str, ...]) -> str:
        if status in {"CLOSED", "CANCELLED", "EXPIRED", "REJECTED"}:
            return "EXITED" if status == "CLOSED" else status
        if "TRAILING_UPDATED" in event_types:
            return "TRAILING"
        if "TARGET_1_HIT" in event_types:
            return "TP1"
        if status in {"OPEN", "PARTIALLY_EXITED"}:
            return "ACTIVE"
        if "ENTRY_FILLED" in event_types:
            return "ENTERED"
        if "ENTRY_PENDING" in event_types:
            return "WAITING"
        return "CREATED"

    @staticmethod
    def _milestones(event_types: tuple[str, ...]) -> tuple[str, ...]:
        mapping = (
            ("TRADE_CREATED", "CREATED"),
            ("ENTRY_PENDING", "WAITING"),
            ("ENTRY_FILLED", "ENTERED"),
            ("TARGET_1_HIT", "TP1_HIT"),
            ("TRAILING_UPDATED", "TRAILING_ACTIVE"),
            ("TARGET_2_HIT", "TP2_HIT"),
            ("EXIT_FILLED", "EXITED"),
        )
        return tuple(label for event_type, label in mapping if event_type in event_types)

    @staticmethod
    def _initial_risk_per_unit(trade: PaperTrade) -> float | None:
        if trade.intended_entry is None or trade.initial_stop_loss is None:
            return None
        risk = abs(float(trade.intended_entry) - float(trade.initial_stop_loss))
        return round(risk, 6) if risk > 0 else None

    @staticmethod
    def _realized_r_multiple(
        realized_pnl: float,
        risk_per_unit: float | None,
        quantity: int,
    ) -> float | None:
        total_initial_risk = (risk_per_unit or 0.0) * int(quantity)
        if total_initial_risk <= 0:
            return None
        return round(float(realized_pnl) / total_initial_risk, 6)

    @staticmethod
    def _holding_seconds(opened_at: str | None, closed_at: str | None) -> float | None:
        if not opened_at:
            return None
        end = closed_at or opened_at
        start_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round(max(0.0, (end_dt - start_dt).total_seconds()), 3)
