"""Configured, broker-symbol-safe CQRP paper-research universe."""

from __future__ import annotations

import os

from src.market_data.contracts import OptionChainRequest


INDEX_REQUESTS = {
    # The mapping is explicit so session data can prove which FYERS symbol
    # supplied each index observation.  ``strike_count=10`` is the research
    # core window; returned provider rows are retained without CQRP filtering.
    "NIFTY": OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", "", 10, capture_profile="research_core_v1"),
    "BANKNIFTY": OptionChainRequest("BANKNIFTY", "NSE:NIFTYBANK-INDEX", "", 10, capture_profile="research_core_v1"),
    "FINNIFTY": OptionChainRequest("FINNIFTY", "NSE:FINNIFTY-INDEX", "", 10, capture_profile="research_core_v1"),
}


def configured_index_requests(value: str | None = None) -> tuple[OptionChainRequest, ...]:
    """Read CQRP_FYERS_INDEX_UNIVERSE; unknown names fail safely at startup."""
    names = (value if value is not None else os.getenv("CQRP_FYERS_INDEX_UNIVERSE", "NIFTY,BANKNIFTY,FINNIFTY"))
    requested = tuple(item.strip().upper() for item in names.split(",") if item.strip())
    unknown = tuple(name for name in requested if name not in INDEX_REQUESTS)
    if unknown:
        raise ValueError("Unsupported CQRP FYERS index instrument(s): " + ", ".join(unknown))
    if not requested:
        raise ValueError("CQRP_FYERS_INDEX_UNIVERSE must contain at least one instrument")
    return tuple(INDEX_REQUESTS[name] for name in requested)
