"""Pure, deterministic risk evaluation for CQRP paper-trading research."""

from __future__ import annotations

from src.signal.models import ResearchSignal

from .config import RiskConfig
from .models import Portfolio, RiskDecision


class PortfolioRiskEngine:
    """Evaluate a persisted recommendation without submitting an order."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def _requested_quantity(self, signal: ResearchSignal, portfolio: Portfolio) -> int:
        entry = float(signal.entry_price or 0.0)
        stop = signal.stop_loss
        method = self.config.sizing_method
        if method == "FIXED_QUANTITY":
            return self.config.fixed_quantity
        if method == "FIXED_CAPITAL":
            return int(self.config.fixed_capital / entry) if entry > 0 else 0
        if method == "FIXED_RISK":
            distance = abs(entry - float(stop)) if stop is not None else 0.0
            return int(self.config.fixed_risk / distance) if distance > 0 else 0
        if method == "PERCENT_PORTFOLIO":
            return int(portfolio.initial_capital * self.config.portfolio_percent / entry) if entry > 0 else 0
        # Deliberately a framework only: volatility input is not part of frozen signals yet.
        return 0

    def evaluate(
        self,
        signal: ResearchSignal,
        portfolio: Portfolio,
        *,
        invested: float = 0.0,
        total_risk: float = 0.0,
        open_positions: int = 0,
        daily_pnl: float = 0.0,
        max_drawdown: float = 0.0,
        instrument_exposure: float = 0.0,
        expiry_exposure: float = 0.0,
        option_type_exposure: float = 0.0,
        experiment_id: str | None = None,
    ) -> RiskDecision:
        entry = float(signal.entry_price or 0.0)
        stop = signal.stop_loss
        requested = self._requested_quantity(signal, portfolio)
        available = max(0.0, portfolio.initial_capital * (1 - self.config.cash_reserve_percent) - invested)
        unit_risk = abs(entry - float(stop)) if stop is not None else 0.0
        reasons: list[str] = []

        if signal.signal_type not in {"BUY", "SELL"}:
            reasons.append("signal is not eligible")
        if requested < 1:
            reasons.append("sizing produced zero quantity")
        if daily_pnl <= -self.config.max_daily_loss:
            reasons.append("daily loss limit breached")
        if max_drawdown >= self.config.max_drawdown:
            reasons.append("drawdown protection triggered")
        if open_positions >= self.config.max_open_positions:
            reasons.append("open-position limit reached")

        approved = requested
        decision = "APPROVED"
        if entry <= 0:
            reasons.append("entry price is invalid")
        elif entry * approved > available:
            reduced = int(available / entry)
            if reduced > 0:
                approved = reduced
                decision = "REDUCED_SIZE"
                reasons.append("quantity reduced to available capital")
            else:
                reasons.append("insufficient available capital")
                approved = 0
        risk = unit_risk * approved
        capital = entry * approved

        if risk > self.config.max_risk_per_trade or total_risk + risk > self.config.max_portfolio_risk:
            reasons.append("risk limit breached")
        if instrument_exposure + capital > self.config.max_instrument_exposure:
            reasons.append("instrument exposure limit breached")
        if expiry_exposure + capital > self.config.max_expiry_exposure:
            reasons.append("expiry exposure limit breached")
        if option_type_exposure + capital > self.config.max_option_type_exposure:
            reasons.append("option type exposure limit breached")

        rejection_reasons = [reason for reason in reasons if reason != "quantity reduced to available capital"]
        if rejection_reasons:
            decision, approved, capital, risk = "REJECTED", 0, 0.0, 0.0

        return RiskDecision.new(
            signal_id=signal.signal_id,
            portfolio_id=portfolio.portfolio_id,
            experiment_id=experiment_id,
            risk_version=self.config.risk_version,
            decision=decision,
            requested_quantity=requested,
            approved_quantity=approved,
            capital_required=capital,
            capital_available=available,
            rejection_reason="; ".join(rejection_reasons) if rejection_reasons else None,
            risk_metrics={
                "unit_risk": unit_risk, "approved_risk": risk, "invested": invested,
                "total_risk": total_risk, "open_positions": open_positions,
                "daily_pnl": daily_pnl, "max_drawdown": max_drawdown,
                "instrument_exposure": instrument_exposure, "expiry_exposure": expiry_exposure,
                "option_type_exposure": option_type_exposure,
            },
        )
