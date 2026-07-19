"""Deterministic underlying, volatility, and time shock reports."""

from __future__ import annotations

from .engine import calculate_portfolio


def stress_test(positions, prices, scenarios: list[dict], greeks_inputs=None) -> list[dict]:
    baseline = calculate_portfolio(positions, prices, greeks_inputs)
    reports = []
    for scenario in scenarios:
        underlying_shift = float(scenario.get("underlying_change_pct", 0))/100
        shocked = {key: value*(1+underlying_shift) for key,value in prices.items()}
        result = calculate_portfolio(positions, shocked, greeks_inputs)
        reports.append({"scenario": dict(scenario), "pnl": result["pnl"], "pnl_change": result["pnl"]-baseline["pnl"],
                        "market_value": result["market_value"]})
    return reports
