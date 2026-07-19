"""Pure deterministic metric calculations with no database or execution dependencies."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from math import sqrt
from statistics import mean, pstdev
from typing import Callable, Iterable

from src.common.version import ANALYTICS_ENGINE_VERSION

from .models import AnalyticsReport, CompletedTrade


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PerformanceAnalyticsEngine:
    """Calculate stable reports from a fixed ordered set of completed paper trades."""

    analytics_version = ANALYTICS_ENGINE_VERSION

    @staticmethod
    def _fingerprint(trades: Iterable[CompletedTrade], scope: dict[str, object]) -> str:
        values = [str(sorted(scope.items()))]
        values.extend(
            f"{t.trade_id}|{t.closed_at}|{t.realized_pnl:.8f}|{t.mae:.8f}|{t.mfe:.8f}"
            for t in sorted(trades, key=lambda item: (item.closed_at, item.trade_id))
        )
        return sha256("\n".join(values).encode()).hexdigest()

    @staticmethod
    def _metrics(trades: list[CompletedTrade]) -> dict[str, float | int | None]:
        ordered = sorted(trades, key=lambda item: (item.closed_at, item.trade_id))
        pnl = [float(t.realized_pnl) for t in ordered]
        winners, losers, flat = [x for x in pnl if x > 0], [x for x in pnl if x < 0], [x for x in pnl if x == 0]
        total = len(pnl)
        gross_profit, gross_loss = sum(winners), sum(losers)
        net = gross_profit + gross_loss
        average_winner = mean(winners) if winners else 0.0
        average_loser = mean(losers) if losers else 0.0
        payoff = average_winner / abs(average_loser) if average_loser else None
        profit_factor = gross_profit / abs(gross_loss) if gross_loss else None
        holdings = [(_time(t.closed_at) - _time(t.opened_at)).total_seconds() for t in ordered]
        equity, peak, drawdowns, max_wins, max_losses = 0.0, 0.0, [], 0, 0
        win_streak = loss_streak = 0
        for value in pnl:
            equity += value
            peak = max(peak, equity)
            drawdowns.append(peak - equity)
            if value > 0:
                win_streak, loss_streak = win_streak + 1, 0
            elif value < 0:
                loss_streak, win_streak = loss_streak + 1, 0
            else:
                win_streak = loss_streak = 0
            max_wins, max_losses = max(max_wins, win_streak), max(max_losses, loss_streak)
        max_drawdown = max(drawdowns, default=0.0)
        returns = [value / max(abs((t.entry_price or 0.0) * t.quantity), 1.0) for value, t in zip(pnl, ordered)]
        return_std = pstdev(returns) if len(returns) > 1 else 0.0
        sharpe = mean(returns) / return_std * sqrt(len(returns)) if return_std else None
        downside = [min(0.0, item) for item in returns]
        downside_std = sqrt(sum(item * item for item in downside) / len(downside)) if downside else 0.0
        sortino = mean(returns) / downside_std * sqrt(len(returns)) if downside_std else None
        sqn_std = pstdev(pnl) if len(pnl) > 1 else 0.0
        sqn = mean(pnl) / sqn_std * sqrt(total) if sqn_std else None
        win_rate = len(winners) / total if total else 0.0
        loss_rate = len(losers) / total if total else 0.0
        kelly = win_rate - (loss_rate / payoff) if payoff else None
        return {
            "total_trades": total, "winning_trades": len(winners), "losing_trades": len(losers),
            "breakeven_trades": len(flat), "win_rate": round(win_rate, 8), "loss_rate": round(loss_rate, 8),
            "gross_profit": round(gross_profit, 8), "gross_loss": round(gross_loss, 8), "net_profit": round(net, 8),
            "average_winner": round(average_winner, 8), "average_loser": round(average_loser, 8),
            "profit_factor": round(profit_factor, 8) if profit_factor is not None else None,
            "expectancy": round(net / total, 8) if total else 0.0,
            "payoff_ratio": round(payoff, 8) if payoff is not None else None,
            "recovery_factor": round(net / max_drawdown, 8) if max_drawdown else None,
            "maximum_drawdown": round(max_drawdown, 8), "current_drawdown": round(drawdowns[-1], 8) if drawdowns else 0.0,
            "average_drawdown": round(mean(drawdowns), 8) if drawdowns else 0.0,
            "maximum_consecutive_wins": max_wins, "maximum_consecutive_losses": max_losses,
            "largest_winning_trade": round(max(winners), 8) if winners else 0.0,
            "largest_losing_trade": round(min(losers), 8) if losers else 0.0,
            "average_mae": round(mean([t.mae for t in ordered]), 8) if total else 0.0,
            "average_mfe": round(mean([t.mfe for t in ordered]), 8) if total else 0.0,
            "average_holding_seconds": round(mean(holdings), 8) if holdings else 0.0,
            "sharpe_ratio": round(sharpe, 8) if sharpe is not None else None,
            "sortino_ratio": round(sortino, 8) if sortino is not None else None,
            "calmar_ratio": round(net / max_drawdown, 8) if max_drawdown else None,
            "omega_ratio": None, "sqn": round(sqn, 8) if sqn is not None else None,
            "kelly_percentage": round(kelly, 8) if kelly is not None else None,
        }

    def equity_curve(self, trades: Iterable[CompletedTrade]) -> list[dict[str, float | str]]:
        equity = peak = 0.0
        curve = []
        for trade in sorted(trades, key=lambda item: (item.closed_at, item.trade_id)):
            equity += trade.realized_pnl
            peak = max(peak, equity)
            curve.append({"trade_id": trade.trade_id, "observed_at": trade.closed_at,
                          "pnl": round(trade.realized_pnl, 8), "equity": round(equity, 8),
                          "drawdown": round(peak - equity, 8)})
        return curve

    def report(
        self, trades: Iterable[CompletedTrade], *, report_type: str = "STRATEGY",
        scope: dict[str, object] | None = None, group_by: str | None = None,
    ) -> AnalyticsReport:
        items = sorted(trades, key=lambda item: (item.closed_at, item.trade_id))
        scope = dict(scope or {})
        groups: dict[str, object] = {}
        if group_by:
            values: dict[str, list[CompletedTrade]] = defaultdict(list)
            extractor: Callable[[CompletedTrade], object] = lambda item: getattr(item, group_by, None)
            for item in items:
                values[str(extractor(item) or "UNSPECIFIED")].append(item)
            groups = {key: self._metrics(value) for key, value in sorted(values.items())}
        return AnalyticsReport.new(
            report_type=report_type, analytics_version=self.analytics_version, scope=scope,
            source_fingerprint=self._fingerprint(items, scope), metrics=self._metrics(items), groups=groups,
        )

    def strategy_comparison(self, trades: Iterable[CompletedTrade]) -> AnalyticsReport:
        return self.report(trades, report_type="STRATEGY_COMPARISON", group_by="strategy_version")

    def scenario_analysis(self, trades: Iterable[CompletedTrade]) -> AnalyticsReport:
        return self.report(trades, report_type="SCENARIO", group_by="scenario")

    def validation_analysis(self, trades: Iterable[CompletedTrade]) -> AnalyticsReport:
        return self.report(trades, report_type="VALIDATION_CONFIDENCE", group_by="confidence_band")
