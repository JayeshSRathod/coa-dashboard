from __future__ import annotations

from src.execution.lifecycle import PaperTradeLifecycleEngine
from src.execution.models import PaperTrade, TradeEvent


def _trade(**overrides):
    values = {
        "signal_id": "sig-1",
        "session_id": "session-1",
        "snapshot_id": "snap-1",
        "experiment_id": "exp-1",
        "strategy_version": "strategy-v1",
        "execution_version": "paper-v1",
        "instrument": "NIFTY",
        "direction": "BUY",
        "expiry": "2026-08-06",
        "strike": 25000.0,
        "option_type": "CE",
        "quantity": 100,
        "intended_entry": 100.0,
        "initial_stop_loss": 90.0,
        "initial_target_1": 115.0,
        "initial_target_2": 130.0,
        "initial_trailing_reference": None,
    }
    values.update(overrides)
    return PaperTrade.new(**values)


def _event(trade, event_type, occurred_at, payload=None, snapshot_id=None):
    return TradeEvent.new(
        trade_id=trade.trade_id,
        session_id=trade.session_id,
        source_snapshot_id=snapshot_id,
        event_type=event_type,
        occurred_at=occurred_at,
        payload=payload or {},
    )


def test_pending_trade_is_waiting():
    trade = _trade()
    events = [
        _event(
            trade,
            "TRADE_CREATED",
            "2026-08-03T03:45:00+00:00",
            {
                "quantity": 100,
                "stop_loss": 90.0,
                "target_1": 115.0,
                "target_2": 130.0,
            },
        ),
        _event(trade, "ENTRY_PENDING", "2026-08-03T03:45:01+00:00"),
    ]
    summary = PaperTradeLifecycleEngine().summarize(trade, events)
    assert summary.stage == "WAITING"
    assert summary.status == "PENDING"
    assert summary.quantity_remaining == 100
    assert summary.realized_r_multiple == 0.0


def test_open_trade_reports_active_metrics():
    trade = _trade()
    events = [
        _event(trade, "TRADE_CREATED", "2026-08-03T03:45:00+00:00", {"quantity": 100, "stop_loss": 90.0}),
        _event(trade, "ENTRY_FILLED", "2026-08-03T03:46:00+00:00", {"price": 100.0, "quantity": 100}),
        _event(trade, "MARK_OBSERVED", "2026-08-03T04:00:00+00:00", {"unrealized_pnl": 500.0, "mfe": 700.0, "mae": -200.0}),
    ]
    summary = PaperTradeLifecycleEngine().summarize(trade, events)
    assert summary.stage == "ACTIVE"
    assert summary.status == "OPEN"
    assert summary.entry_price == 100.0
    assert summary.unrealized_pnl == 500.0
    assert summary.mfe == 700.0
    assert summary.mae == -200.0


def test_partial_exit_and_trailing_stage():
    trade = _trade()
    events = [
        _event(trade, "TRADE_CREATED", "2026-08-03T03:45:00+00:00", {"quantity": 100, "stop_loss": 90.0}),
        _event(trade, "ENTRY_FILLED", "2026-08-03T03:46:00+00:00", {"price": 100.0, "quantity": 100}),
        _event(trade, "TARGET_1_HIT", "2026-08-03T04:10:00+00:00"),
        _event(trade, "PARTIAL_EXIT", "2026-08-03T04:10:01+00:00", {"quantity": 50, "price": 115.0, "realized_pnl_delta": 750.0, "reason": "TARGET_1"}),
        _event(trade, "STOP_LOSS_MOVED", "2026-08-03T04:10:02+00:00", {"stop_loss": 100.0}),
        _event(trade, "TRAILING_UPDATED", "2026-08-03T04:10:03+00:00", {"trailing_reference": 100.0}),
    ]
    summary = PaperTradeLifecycleEngine().summarize(trade, events)
    assert summary.stage == "TRAILING"
    assert summary.status == "PARTIALLY_EXITED"
    assert summary.quantity_remaining == 50
    assert summary.realized_pnl == 750.0
    assert summary.metrics["target_1_hit"] is True
    assert summary.metrics["trailing_activated"] is True


def test_closed_trade_calculates_r_multiple_and_holding_time():
    trade = _trade()
    events = [
        _event(trade, "TRADE_CREATED", "2026-08-03T03:45:00+00:00", {"quantity": 100, "stop_loss": 90.0}),
        _event(trade, "ENTRY_FILLED", "2026-08-03T03:46:00+00:00", {"price": 100.0, "quantity": 100}),
        _event(trade, "TARGET_2_HIT", "2026-08-03T04:16:00+00:00"),
        _event(trade, "EXIT_FILLED", "2026-08-03T04:16:00+00:00", {"quantity": 100, "price": 130.0, "realized_pnl_delta": 3000.0, "reason": "TARGET_2"}),
    ]
    summary = PaperTradeLifecycleEngine().summarize(trade, events)
    assert summary.stage == "EXITED"
    assert summary.status == "CLOSED"
    assert summary.quantity_remaining == 0
    assert summary.average_exit_price == 130.0
    assert summary.realized_r_multiple == 3.0
    assert summary.holding_seconds == 1800.0
    assert summary.exit_reason == "TARGET_2"
    assert summary.milestones[-1] == "EXITED"


def test_cancelled_trade_is_not_treated_as_exit():
    trade = _trade()
    events = [
        _event(trade, "TRADE_CREATED", "2026-08-03T03:45:00+00:00", {"quantity": 100}),
        _event(trade, "TRADE_CANCELLED", "2026-08-03T03:50:00+00:00", {"reason": "VALIDATION_FAILED"}),
    ]
    summary = PaperTradeLifecycleEngine().summarize(trade, events)
    assert summary.stage == "CANCELLED"
    assert summary.status == "CANCELLED"
    assert summary.exit_reason == "VALIDATION_FAILED"
