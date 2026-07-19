"""Pure portfolio and position analytics."""

from __future__ import annotations

from .greeks import calculate_greeks


def calculate_position(position: dict, market_price: float, greeks_input: dict | None = None) -> dict:
    quantity = float(position["quantity"])
    entry = float(position["average_price"])
    value = quantity * market_price
    pnl = quantity * (market_price - entry)
    result = {"position_id": position.get("position_id"), "symbol": position["symbol"], "quantity": quantity,
              "average_price": entry, "current_price": market_price, "market_value": value, "pnl": pnl,
              "pnl_percent": (pnl / abs(quantity * entry) * 100) if quantity and entry else 0.0,
              "capital_used": abs(quantity * entry)}
    if greeks_input:
        greeks = calculate_greeks(**greeks_input)
        result["greeks"] = {name: getattr(greeks, name) * quantity for name in ("delta", "gamma", "theta", "vega", "rho")}
    return result


def calculate_portfolio(positions: list[dict], prices: dict[str, float], greeks_inputs: dict[str, dict] | None = None) -> dict:
    analyses = [calculate_position(p, prices[p["position_id"]], (greeks_inputs or {}).get(p["position_id"])) for p in positions]
    totals = {key: sum(float(item[key]) for item in analyses) for key in ("market_value", "pnl", "capital_used")}
    totals["available_capital"] = None
    totals["positions"] = analyses
    totals["portfolio_greeks"] = {metric: sum(item.get("greeks", {}).get(metric, 0.0) for item in analyses)
                                  for metric in ("delta", "gamma", "theta", "vega", "rho")}
    totals["largest_position"] = max(analyses, key=lambda item: abs(item["market_value"]), default=None)
    return totals
