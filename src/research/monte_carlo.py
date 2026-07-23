"""Seeded Monte Carlo trade-order robustness simulation."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable

from .metrics import performance_metrics


@dataclass(frozen=True)
class MonteCarloResult:
    seed: int
    simulations: int
    net_profit_range: tuple[float, float]
    worst_case_drawdown: float


class MonteCarloSimulator:
    def simulate(self, pnls: Iterable[float], *, simulations: int = 100, seed: int = 0) -> MonteCarloResult:
        if simulations < 1:
            raise ValueError("simulations must be positive")
        source = tuple(float(value) for value in pnls)
        random = Random(seed)
        metrics = []
        for _ in range(simulations):
            shuffled = list(source)
            random.shuffle(shuffled)
            metrics.append(performance_metrics(shuffled))
        profits = tuple(float(item["net_profit"]) for item in metrics)
        drawdowns = tuple(float(item["maximum_drawdown"]) for item in metrics)
        return MonteCarloResult(seed, simulations, (min(profits, default=0.0), max(profits, default=0.0)), max(drawdowns, default=0.0))
