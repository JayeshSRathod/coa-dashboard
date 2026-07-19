"""Deterministic option-chain, OI, IV, and max-pain calculations."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean


def analyze_option_chain(chain: list[dict], spot: float) -> dict:
    calls = [row for row in chain if row["option_type"].upper() == "CALL"]
    puts = [row for row in chain if row["option_type"].upper() == "PUT"]
    call_oi, put_oi = sum(float(row.get("oi", 0)) for row in calls), sum(float(row.get("oi", 0)) for row in puts)
    atm = min(chain, key=lambda row: abs(float(row["strike"]) - spot))["strike"] if chain else None
    return {
        "atm": atm, "pcr": (put_oi / call_oi) if call_oi else None,
        "call_oi": call_oi, "put_oi": put_oi,
        "highest_call_oi": max(calls, key=lambda row: (float(row.get("oi", 0)), -float(row["strike"])), default=None),
        "highest_put_oi": max(puts, key=lambda row: (float(row.get("oi", 0)), -float(row["strike"])), default=None),
        "average_spread": fmean([float(row.get("ask", 0)) - float(row.get("bid", 0)) for row in chain]) if chain else 0.0,
    }


def classify_oi_change(*, price_change: float, oi_change: float) -> str:
    if price_change >= 0 and oi_change >= 0: return "LONG_BUILDUP"
    if price_change < 0 and oi_change >= 0: return "SHORT_BUILDUP"
    if price_change < 0 and oi_change < 0: return "LONG_UNWINDING"
    return "SHORT_COVERING"


def iv_statistics(current_iv: float, history: list[float]) -> dict:
    values = [float(v) for v in history]
    if not values: raise ValueError("IV history is required")
    low, high = min(values), max(values)
    return {"current_iv": current_iv, "average_iv": fmean(values), "highest_iv": high, "lowest_iv": low,
            "iv_rank": ((current_iv-low)/(high-low)*100) if high != low else 0.0,
            "iv_percentile": sum(v <= current_iv for v in values)/len(values)*100}


def max_pain(chain: list[dict]) -> dict:
    strikes = sorted({float(row["strike"]) for row in chain})
    pain = {}
    for settlement in strikes:
        pain[settlement] = sum(
            (
                max(0.0, settlement - float(row["strike"])) * float(row.get("oi", 0))
                if row["option_type"].upper() == "CALL"
                else max(0.0, float(row["strike"]) - settlement) * float(row.get("oi", 0))
            )
            for row in chain
        )
    level = min(pain, key=lambda strike: (pain[strike], strike)) if pain else None
    return {"max_pain": level, "pain_by_strike": pain}
