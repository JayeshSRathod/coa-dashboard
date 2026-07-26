"""Configured, broker-symbol-safe CQRP paper-research universe."""

from __future__ import annotations

import os

from src.market_data.contracts import OptionChainRequest


INDEX_REQUESTS = {
    "NIFTY": OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", "", 10),
    "BANKNIFTY": OptionChainRequest("BANKNIFTY", "NSE:NIFTYBANK-INDEX", "", 10),
    "FINNIFTY": OptionChainRequest("FINNIFTY", "NSE:FINNIFTY-INDEX", "", 10),
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
