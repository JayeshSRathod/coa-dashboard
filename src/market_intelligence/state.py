"""Independent, deterministic market-state and technical evidence from spot history."""

from __future__ import annotations

from math import sqrt


def market_state(spots: list[float]) -> dict[str, object]:
    values = [float(value) for value in spots]
    if len(values) < 5:
        return {"state": "INSUFFICIENT_HISTORY", "observations": len(values), "reason": "five snapshots are required"}
    short = sum(values[-3:]) / 3
    long = sum(values[-5:]) / 5
    change = (values[-1] - values[-5]) / values[-5] * 100 if values[-5] else 0.0
    variance = sum((value - long) ** 2 for value in values[-5:]) / 5
    volatility = sqrt(variance) / long * 100 if long else 0.0
    state = "TRENDING_UP" if short > long and change > 0.03 else ("TRENDING_DOWN" if short < long and change < -0.03 else "RANGE_BOUND")
    if volatility >= 0.35:
        state = "VOLATILE_" + state
    return {"state": state, "observations": len(values), "change_pct": round(change, 4), "volatility_pct": round(volatility, 4), "short_average": round(short, 4), "long_average": round(long, 4)}


def technical_confirmation(spots: list[float]) -> dict[str, object]:
    values = [float(value) for value in spots]
    if len(values) < 5:
        return {"status": "WAIT", "score": 0.0, "reason": "five spot observations are required", "available": ["EMA", "Bollinger", "momentum"]}
    ema = values[0]
    for value in values[1:]:
        ema = value * (2 / 6) + ema * (1 - 2 / 6)
    mean = sum(values[-5:]) / 5
    deviation = sqrt(sum((value - mean) ** 2 for value in values[-5:]) / 5)
    momentum = (values[-1] - values[-3]) / values[-3] * 100 if values[-3] else 0.0
    bullish = values[-1] > ema and momentum > 0
    bearish = values[-1] < ema and momentum < 0
    score = 80.0 if bullish or bearish else 45.0
    return {"status": "PASS" if score >= 80 else "WAIT", "score": score, "bias": "BULLISH" if bullish else ("BEARISH" if bearish else "NEUTRAL"), "ema_5": round(ema, 4), "bollinger_lower": round(mean - 2 * deviation, 4), "bollinger_upper": round(mean + 2 * deviation, 4), "momentum_pct": round(momentum, 4), "note": "ADX and Hull require FYERS candle/history ingestion and are not inferred from option-chain snapshots."}
