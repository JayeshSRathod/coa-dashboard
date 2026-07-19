"""Pure fill-cost and slippage calculations for paper execution."""

from __future__ import annotations

from .config import PaperExecutionConfig


def apply_slippage(price: float, *, is_entry: bool, config: PaperExecutionConfig) -> float:
    adjustment = config.fixed_slippage + price * config.percentage_slippage
    return price + adjustment if is_entry else max(0.0, price - adjustment)


def transaction_cost(price: float, quantity: int, config: PaperExecutionConfig) -> float:
    notional = abs(price * quantity)
    return round(
        notional * (config.brokerage_rate + config.exchange_charge_rate + config.tax_rate)
        + config.fixed_cost_per_fill, 8
    )
