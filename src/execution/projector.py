"""Pure event-stream reducer for current simulated-trade state."""

from __future__ import annotations

from collections.abc import Iterable

from .models import PaperTrade, TradeEvent, TradeState


def project_trade(trade: PaperTrade, events: Iterable[TradeEvent]) -> TradeState:
    status, remaining = "PENDING", 0
    entry = stop = target1 = target2 = trail = None
    opened = closed = reason = None
    realized = unrealized = mfe = mae = 0.0
    exit_notional = exit_qty = 0
    for event in events:
        payload = event.payload
        if event.event_type == "TRADE_CREATED":
            remaining = int(payload.get("quantity", trade.quantity))
            stop, target1, target2, trail = (payload.get("stop_loss"), payload.get("target_1"),
                                              payload.get("target_2"), payload.get("trailing_reference"))
        elif event.event_type == "ENTRY_FILLED":
            status, entry, opened = "OPEN", float(payload["price"]), event.occurred_at
        elif event.event_type == "ENTRY_REJECTED":
            status, closed, reason = "REJECTED", event.occurred_at, payload.get("reason")
        elif event.event_type in {"TRADE_CANCELLED", "TRADE_EXPIRED"}:
            status, closed, reason = ("CANCELLED" if event.event_type == "TRADE_CANCELLED" else "EXPIRED",
                                      event.occurred_at, payload.get("reason"))
        elif event.event_type == "STOP_LOSS_MOVED":
            stop = payload.get("stop_loss")
        elif event.event_type == "TRAILING_UPDATED":
            trail = payload.get("trailing_reference")
        elif event.event_type == "MARK_OBSERVED":
            unrealized, mfe, mae = (float(payload.get("unrealized_pnl", unrealized)),
                                    max(mfe, float(payload.get("mfe", mfe))),
                                    min(mae, float(payload.get("mae", mae))))
        elif event.event_type in {"PARTIAL_EXIT", "EXIT_FILLED"}:
            quantity = int(payload.get("quantity", remaining))
            remaining = max(0, remaining - quantity)
            realized += float(payload.get("realized_pnl_delta", 0))
            exit_notional += float(payload.get("price", 0)) * quantity
            exit_qty += quantity
            if event.event_type == "PARTIAL_EXIT" and remaining:
                status = "PARTIALLY_EXITED"
            else:
                status, closed, reason = "CLOSED", event.occurred_at, payload.get("reason")
    average_exit = exit_notional / exit_qty if exit_qty else None
    return TradeState(
        trade_id=trade.trade_id, status=status, quantity_remaining=remaining,
        executed_entry=entry, stop_loss=stop, target_1=target1, target_2=target2,
        trailing_reference=trail, average_exit_price=average_exit, realized_pnl=round(realized, 8),
        unrealized_pnl=round(unrealized, 8), mfe=round(mfe, 8), mae=round(mae, 8),
        opened_at=opened, closed_at=closed, exit_reason=reason,
    )
