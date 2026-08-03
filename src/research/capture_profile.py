"""Research-only capture profile metadata.

This module records what the feed supplied and which strike window was
requested.  It deliberately does not rank strikes, alter COA inputs, or make
any execution decision.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def capture_metadata(*, profile: str, provider_symbol: str | None, requested_expiry: str | None,
                     resolved_expiry: str | None, spot: float, atm_strike: float | None,
                     strikes: list[float], strike_count: int | None) -> dict[str, Any]:
    """Return an immutable description of the observation window."""
    return {
        "capture_profile": profile,
        "provider_symbol": provider_symbol,
        "requested_expiry": requested_expiry,
        "resolved_expiry": resolved_expiry,
        "days_to_expiry": _days_to_expiry(resolved_expiry),
        "strike_window": {
            "requested_intervals": strike_count,
            "atm_strike": atm_strike,
            "returned_strike_count": len(strikes),
            "lowest_strike": min(strikes) if strikes else None,
            "highest_strike": max(strikes) if strikes else None,
            "selection": "provider_returned_chain; no CQRP strike filtering",
        },
        "observation_scope": "research_only",
    }


def _days_to_expiry(expiry: str | None, now: datetime | None = None) -> int | None:
    if not expiry:
        return None
    try:
        expiry_date = date.fromisoformat(str(expiry)[:10])
    except ValueError:
        return None
    return (expiry_date - (now.date() if now else datetime.now().date())).days
