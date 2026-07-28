"""Presentation-only option-chain ladder models for CQRP Dashboard."""

from __future__ import annotations

from typing import Any, Iterable


def build_option_ladder(option_chain: Iterable[dict[str, Any]], spot: float | None) -> list[dict[str, Any]]:
    """Create one CE-left / strike-centre / PE-right row per captured strike."""
    source_rows = list(option_chain)
    rows: list[dict[str, Any]] = []
    for source in sorted(source_rows, key=lambda item: _number(item.get("Strike")) or 0.0):
        strike = _number(source.get("Strike"))
        if strike is None:
            continue
        row = {"strike": strike, "is_atm": _is_atm(strike, spot, source_rows)}
        for prefix, label in (("ce", "Call"), ("pe", "Put")):
            row.update({
                f"{prefix}_oi": _number(source.get(f"{label}_OI")),
                f"{prefix}_oi_change": _number(source.get(f"{label}_OI_Change")),
                f"{prefix}_volume": _number(source.get(f"{label}_Vol")),
                f"{prefix}_bid": _number(source.get(f"{label}_Bid")),
                f"{prefix}_ask": _number(source.get(f"{label}_Ask")),
                f"{prefix}_ltp": _number(source.get(f"{label}_LTP")),
                f"{prefix}_iv": _number(source.get(f"{label}_IV")),
                f"{prefix}_delta": _number(source.get(f"{label}_Delta")),
                f"{prefix}_gamma": _number(source.get(f"{label}_Gamma")),
                f"{prefix}_theta": _number(source.get(f"{label}_Theta")),
                f"{prefix}_vega": _number(source.get(f"{label}_Vega")),
            })
            bid, ask = row[f"{prefix}_bid"], row[f"{prefix}_ask"]
            row[f"{prefix}_spread"] = ask - bid if bid is not None and ask is not None else None
        rows.append(row)
    return rows


def filter_ladder_around_atm(rows: Iterable[dict[str, Any]], count_each_side: int) -> list[dict[str, Any]]:
    ordered = list(rows)
    if not ordered:
        return []
    atm_index = next((index for index, row in enumerate(ordered) if row.get("is_atm")), len(ordered) // 2)
    start = max(0, atm_index - max(0, int(count_each_side)))
    end = min(len(ordered), atm_index + max(0, int(count_each_side)) + 1)
    return ordered[start:end]


def _is_atm(strike: float, spot: float | None, option_chain: Iterable[dict[str, Any]]) -> bool:
    if spot is None:
        return False
    strikes = [_number(row.get("Strike")) for row in option_chain]
    valid = [value for value in strikes if value is not None]
    return bool(valid) and strike == min(valid, key=lambda value: abs(value - float(spot)))


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
