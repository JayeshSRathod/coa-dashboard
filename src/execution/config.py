"""Configuration boundary for deterministic paper fills, costs, and lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperExecutionConfig:
    execution_version: str = "1.0.0"
    fill_policy: str = "NEXT_SNAPSHOT"
    entry_price_source: str = "ASK"
    exit_price_source: str = "BID"
    ambiguity_policy: str = "CONSERVATIVE"
    target_1_fraction: float = 0.5
    trailing_mode: str = "BREAKEVEN_AFTER_T1"
    stop_loss_range_fraction: float = 0.10
    fixed_slippage: float = 0.0
    percentage_slippage: float = 0.0
    brokerage_rate: float = 0.0
    exchange_charge_rate: float = 0.0
    tax_rate: float = 0.0
    fixed_cost_per_fill: float = 0.0
    minimum_lot_size: int = 1
    default_quantity: int = 1
    session_end_policy: str = "FORCE_CLOSE"

    def __post_init__(self) -> None:
        if self.fill_policy not in {"NEXT_SNAPSHOT", "TOUCH_PRICE", "CLOSE_CONFIRMATION"}:
            raise ValueError("unsupported fill_policy")
        if self.entry_price_source not in {"LTP", "MID_PRICE", "BID", "ASK", "CLOSE"}:
            raise ValueError("unsupported entry_price_source")
        if self.exit_price_source not in {"LTP", "MID_PRICE", "BID", "ASK", "CLOSE"}:
            raise ValueError("unsupported exit_price_source")
        if self.ambiguity_policy not in {"CONSERVATIVE", "OPTIMISTIC", "STOP_FIRST", "TARGET_FIRST"}:
            raise ValueError("unsupported ambiguity_policy")
        if self.trailing_mode not in {"NONE", "BREAKEVEN_AFTER_T1", "FIXED_POINTS", "FIXED_PERCENT"}:
            raise ValueError("unsupported trailing_mode")
        if self.session_end_policy not in {"FORCE_CLOSE", "MARK_TO_LAST", "CANCEL_UNFILLED"}:
            raise ValueError("unsupported session_end_policy")
        if not 0 < self.target_1_fraction <= 1:
            raise ValueError("target_1_fraction must be in (0, 1]")
        if self.minimum_lot_size < 1 or self.default_quantity < 1:
            raise ValueError("lot size and quantity must be positive")
        if any(value < 0 for value in (
            self.stop_loss_range_fraction, self.fixed_slippage, self.percentage_slippage,
            self.brokerage_rate, self.exchange_charge_rate, self.tax_rate, self.fixed_cost_per_fill,
        )):
            raise ValueError("paper execution costs and slippage cannot be negative")
