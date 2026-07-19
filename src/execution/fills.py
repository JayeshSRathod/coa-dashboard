"""Provider-neutral option quote lookup for deterministic paper fills."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import PaperExecutionConfig


def _number(row: Mapping[str, Any], names: tuple[str, ...]) -> float | None:
    for name in names:
        try:
            if row.get(name) is not None:
                return float(row[name])
        except (TypeError, ValueError):
            return None
    return None


def option_quote(snapshot: Mapping[str, Any], strike: float | None, option_type: str, source: str) -> float | None:
    chain = snapshot.get("option_chain")
    if not isinstance(chain, list):
        return None
    selected = None
    for row in chain:
        if not isinstance(row, Mapping):
            continue
        row_strike = _number(row, ("Strike", "strike"))
        if strike is None or row_strike == strike:
            selected = row
            if strike is not None:
                break
    if selected is None:
        return None
    prefix = "Call" if option_type == "CE" else "Put"
    aliases = {
        "LTP": (prefix + "_LTP", "CE_LTP" if option_type == "CE" else "PE_LTP"),
        "BID": (prefix + "_Bid", "CE_Bid" if option_type == "CE" else "PE_Bid"),
        "ASK": (prefix + "_Ask", "CE_Ask" if option_type == "CE" else "PE_Ask"),
        "CLOSE": (prefix + "_Close",),
    }
    if source == "MID_PRICE":
        bid, ask = _number(selected, aliases["BID"]), _number(selected, aliases["ASK"])
        return (bid + ask) / 2 if bid is not None and ask is not None else None
    return _number(selected, aliases[source])
