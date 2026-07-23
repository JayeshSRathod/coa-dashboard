"""Deterministic selector functions; no broker or strategy calculations."""
from __future__ import annotations
from typing import Any, Mapping
def select_expiry(snapshot: Mapping[str, Any], horizon: str = "INTRADAY") -> str | None:
    expiries = sorted(str(value) for value in (snapshot.get("metadata") or {}).get("available_expiries", []) if value)
    return expiries[0] if horizon == "INTRADAY" else expiries[-1] if expiries else snapshot.get("expiry")
def select_strike(snapshot: Mapping[str, Any], action: str) -> tuple[float | None, str | None]:
    spot = float(snapshot.get("spot") or 0); rows = snapshot.get("option_chain") or []
    strikes = sorted(float(row.get("Strike", row.get("strike"))) for row in rows if row.get("Strike", row.get("strike")) is not None)
    if not strikes or action not in {"BUY", "SELL"}: return None, None
    strike = min(strikes, key=lambda value: (abs(value - spot), value)); return strike, "CE" if action == "BUY" else "PE"
