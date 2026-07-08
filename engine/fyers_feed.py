"""
Fyers Option Chain Feed
-------------------------
Uses the official fyers-apiv3 SDK for the option chain call itself (Fyers'
own docs pages are a JS app that couldn't be fetched directly, so rather
than guess the raw REST endpoint, this rides on their maintained SDK, which
is verified from PyPI/community sources to expose `.optionchain()`).

parse_fyers_chain() is a pure function, independent of the SDK/network call,
so it's fully unit-testable against a mock response shaped like Fyers'
actual JSON (cross-checked against a community-maintained typed Go client
that mirrors the same field names).

IMPORTANT ASSUMPTION TO VERIFY LIVE: the underlying's own spot price is
assumed to appear as one entry in the "optionsChain" array with no
option_type/strike_price (rather than a separate top-level field). If your
first live test shows this assumption is wrong, use the debug view in the
sidebar to see the raw response and adjust parse_fyers_chain() accordingly.
"""

import pandas as pd


def fetch_fyers_option_chain_raw(app_id: str, access_token: str, symbol: str, strikecount: int = 10) -> dict:
    """Live network call via the fyers-apiv3 SDK. Returns the raw 'data' block."""
    from fyers_apiv3 import fyersModel
    fyers = fyersModel.FyersModel(client_id=app_id, token=access_token, is_async=False, log_path="")
    response = fyers.optionchain(data={"symbol": symbol, "strikecount": str(strikecount), "timestamp": ""})
    if response.get("s") != "ok":
        raise RuntimeError(f"Fyers option chain error: {response}")
    return response["data"]


def parse_fyers_chain(raw_data: dict) -> tuple:
    """
    Pure function — converts Fyers' {"optionsChain": [...], ...} block into
    our standard (DataFrame, live_spot) shape. No network call.
    """
    entries = raw_data.get("optionsChain", [])
    spot = None
    calls, puts = {}, {}

    for e in entries:
        opt_type = (e.get("option_type") or "").upper()
        strike = e.get("strike_price")
        if opt_type not in ("CE", "PE") or not strike:
            if spot is None:
                spot = float(e.get("ltp", 0) or 0)
            continue
        strike = float(strike)
        bucket = calls if opt_type == "CE" else puts
        bucket[strike] = {
            "ltp": float(e.get("ltp", 0) or 0),
            "oi": float(e.get("oi", 0) or 0),
            "volume": float(e.get("volume", 0) or 0),
        }

    if spot is None:
        raise RuntimeError(
            "Could not find the underlying's spot price in the Fyers response "
            "(expected a row with no option_type/strike_price). Use the debug "
            "view to inspect the raw response and adjust parse_fyers_chain()."
        )

    all_strikes = sorted(set(calls) | set(puts))
    empty = {"ltp": 0.0, "oi": 0.0, "volume": 0.0}
    rows = []
    for k in all_strikes:
        c, p = calls.get(k, empty), puts.get(k, empty)
        rows.append({
            "Strike": k,
            "Call_OI": c["oi"], "Call_Vol": c["volume"], "Call_LTP": c["ltp"],
            "Put_LTP": p["ltp"], "Put_Vol": p["volume"], "Put_OI": p["oi"],
        })
    df = pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
    return df, spot


def get_live_fyers_chain(app_id: str, access_token: str, symbol: str, strikecount: int = 10) -> tuple:
    raw = fetch_fyers_option_chain_raw(app_id, access_token, symbol, strikecount)
    return parse_fyers_chain(raw)
