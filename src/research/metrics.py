"""Deterministic, dependency-free performance metrics for research runs.

The functions in this module are deliberately pure.  They consume completed
paper-trade P&L observations and do not access live services, databases, or
the frozen COA engine.
"""

from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev
from typing import Iterable, Mapping


def performance_metrics(pnls: Iterable[float], *, periods_per_year: int = 252) -> dict[str, float | int]:
    """Return reproducible aggregate performance metrics for a P&L sequence."""
    values = tuple(float(value) for value in pnls)
    total = sum(values)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    maximum_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, peak - equity)

    average = mean(values) if values else 0.0
    deviation = pstdev(values) if len(values) > 1 else 0.0
    downside = tuple(min(value, 0.0) for value in values)
    downside_deviation = sqrt(sum(value * value for value in downside) / len(downside)) if downside else 0.0
    sharpe = (average / deviation) * sqrt(periods_per_year) if deviation else 0.0
    sortino = (average / downside_deviation) * sqrt(periods_per_year) if downside_deviation else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    recovery_factor = total / maximum_drawdown if maximum_drawdown else total
    return {
        "total_trades": len(values),
        "net_profit": total,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "win_rate": len(wins) / len(values) if values else 0.0,
        "average_gain": mean(wins) if wins else 0.0,
        "average_loss": mean(losses) if losses else 0.0,
        "profit_factor": profit_factor,
        "expectancy": average,
        "maximum_drawdown": maximum_drawdown,
        "recovery_factor": recovery_factor,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": total / maximum_drawdown if maximum_drawdown else total,
    }


def metric_delta(candidate: Mapping[str, float], benchmark: Mapping[str, float]) -> dict[str, float]:
    """Return a stable candidate-minus-benchmark metric comparison."""
    keys = sorted(set(candidate) | set(benchmark))
    return {key: float(candidate.get(key, 0.0)) - float(benchmark.get(key, 0.0)) for key in keys}
