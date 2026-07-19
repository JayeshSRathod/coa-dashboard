"""Configuration contract for deterministic portfolio risk evaluation."""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_SIZING = {
    "FIXED_QUANTITY", "FIXED_CAPITAL", "FIXED_RISK", "PERCENT_PORTFOLIO", "VOLATILITY_BASED",
}


@dataclass(frozen=True)
class RiskConfig:
    """Versioned, dependency-free controls used by the paper-risk layer."""

    risk_version: str = "1.0.0"
    sizing_method: str = "FIXED_QUANTITY"
    fixed_quantity: int = 1
    fixed_capital: float = 50_000.0
    fixed_risk: float = 2_000.0
    portfolio_percent: float = 0.02
    max_risk_per_trade: float = 5_000.0
    max_portfolio_risk: float = 20_000.0
    max_daily_loss: float = 3_000.0
    max_drawdown: float = 10_000.0
    max_open_positions: int = 3
    max_instrument_exposure: float = 100_000.0
    max_expiry_exposure: float = 100_000.0
    max_option_type_exposure: float = 100_000.0
    cash_reserve_percent: float = 0.10

    def __post_init__(self) -> None:
        if self.sizing_method not in _ALLOWED_SIZING:
            raise ValueError(f"unsupported sizing method: {self.sizing_method}")
        if self.fixed_quantity < 0 or self.max_open_positions < 1:
            raise ValueError("position quantities and limits must be non-negative")
        if not 0 <= self.cash_reserve_percent < 1:
            raise ValueError("cash_reserve_percent must be in [0, 1)")
        if not 0 < self.portfolio_percent <= 1:
            raise ValueError("portfolio_percent must be in (0, 1]")
