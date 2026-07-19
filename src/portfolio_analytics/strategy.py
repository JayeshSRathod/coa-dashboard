"""Deterministic payoff analysis for standard option strategies represented as legs."""

from __future__ import annotations


def analyze_strategy(*, legs: list[dict], underlying_prices: list[float]) -> dict:
    """Calculate payoff grid, extrema, break-even interpolation, and capital requirement."""
    if not legs or not underlying_prices: raise ValueError("legs and underlying_prices are required")
    payoff = {}
    for price in sorted(float(p) for p in underlying_prices):
        total = 0.0
        for leg in legs:
            intrinsic = max(0, price-float(leg["strike"])) if leg["option_type"].upper()=="CALL" else max(0, float(leg["strike"])-price)
            sign = 1 if leg["side"].upper()=="LONG" else -1
            total += sign * (intrinsic-float(leg["premium"])) * float(leg["quantity"])
        payoff[price] = total
    points = sorted(payoff.items())
    break_evens = [p for p,v in points if v == 0]
    for (x1,y1),(x2,y2) in zip(points, points[1:]):
        if y1*y2 < 0: break_evens.append(x1 + (0-y1)*(x2-x1)/(y2-y1))
    return {"payoff": payoff, "maximum_profit": max(payoff.values()), "maximum_loss": min(payoff.values()),
            "break_evens": sorted(break_evens), "capital_requirement": sum(abs(float(l["premium"])*float(l["quantity"])) for l in legs)}
