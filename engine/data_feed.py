"""
Data Feed
---------
generate_simulated_chain() produces a realistic-looking option chain for
local development and testing without needing live broker credentials.

To go live: replace the body of get_option_chain() with a real DhanHQ call
(dhanhq.get_option_chain / WebSocket subscription) that returns a DataFrame
with the same columns: Strike, Call_OI, Call_Vol, Call_LTP, Put_LTP, Put_Vol, Put_OI
"""

import pandas as pd
import requests

DHAN_BASE_URL = "https://api.dhan.co/v2"

# Security IDs are specific to Dhan's instrument master and must be exact —
# a wrong ID returns either an error or, worse, silently wrong data.
# Confirmed from DhanHQ v2 docs: NIFTY 50 = 13, segment IDX_I.
# Other indices aren't wired yet — look theirs up at
# https://dhanhq.co/docs/v2/instruments/ before adding them here.
NIFTY_50_SECURITY_ID = 13
NIFTY_50_SEGMENT = "IDX_I"


def get_expiry_list(client_id: str, access_token: str,
                     security_id: int = NIFTY_50_SECURITY_ID,
                     segment: str = NIFTY_50_SEGMENT) -> list:
    """Live network call — returns list of expiry date strings, e.g. ['2026-07-14', ...]."""
    resp = requests.post(
        f"{DHAN_BASE_URL}/optionchain/expirylist",
        headers={"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"},
        json={"UnderlyingScrip": security_id, "UnderlyingSeg": segment},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Dhan expiry list error: {payload}")
    return payload.get("data", [])


def fetch_dhan_option_chain_raw(client_id: str, access_token: str,
                                 security_id: int, segment: str, expiry: str) -> dict:
    """Live network call — returns the raw Dhan response 'data' block."""
    resp = requests.post(
        f"{DHAN_BASE_URL}/optionchain",
        headers={"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"},
        json={"UnderlyingScrip": security_id, "UnderlyingSeg": segment, "Expiry": expiry},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Dhan option chain error: {payload}")
    return payload["data"]


def parse_dhan_chain(raw_data: dict) -> tuple:
    """
    Pure function — converts Dhan's {"last_price":..., "oc": {...}} block into
    our standard (DataFrame, live_spot) shape. No network call, fully unit-testable.
    """
    spot = float(raw_data["last_price"])
    rows = []
    for strike_str, sides in raw_data["oc"].items():
        ce = sides.get("ce", {}) or {}
        pe = sides.get("pe", {}) or {}
        rows.append({
            "Strike": float(strike_str),
            "Call_OI": ce.get("oi", 0) or 0,
            "Call_Vol": ce.get("volume", 0) or 0,
            "Call_LTP": ce.get("last_price", 0.0) or 0.0,
            "Put_LTP": pe.get("last_price", 0.0) or 0.0,
            "Put_Vol": pe.get("volume", 0) or 0,
            "Put_OI": pe.get("oi", 0) or 0,
        })
    df = pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
    return df, spot


def get_live_chain(client_id: str, access_token: str, security_id: int,
                    segment: str, expiry: str = None) -> tuple:
    """
    Generic entry point for real data on any instrument in the registry.
    If expiry isn't given, uses the nearest available one.
    Raises on any failure — caller (app.py) is responsible for catching this
    and falling back to simulated data, so a Dhan outage never crashes the app.
    """
    if expiry is None:
        expiries = get_expiry_list(client_id, access_token, security_id, segment)
        if not expiries:
            raise RuntimeError(f"No expiries returned from Dhan for security_id={security_id}")
        expiry = expiries[0]
    raw = fetch_dhan_option_chain_raw(client_id, access_token, security_id, segment, expiry)
    return parse_dhan_chain(raw)


def get_live_nifty_chain(client_id: str, access_token: str, expiry: str = None) -> tuple:
    """Backward-compatible convenience wrapper for NIFTY 50 specifically."""
    return get_live_chain(client_id, access_token, NIFTY_50_SECURITY_ID, NIFTY_50_SEGMENT, expiry)


def is_dhan_configured() -> bool:
    try:
        import streamlit as st
        client_id = st.secrets["dhan"]["client_id"]
        access_token = st.secrets["dhan"]["access_token"]
        return bool(client_id) and bool(access_token) and "your-dhan" not in str(client_id)
    except Exception:
        return False


def generate_simulated_chain(spot: float, step: int) -> pd.DataFrame:
    """Simulates a realistic option chain snapshot around the given spot."""
    strikes = [int((spot // step) * step + (i * step)) for i in range(-6, 7)]
    records = []
    base_strike = (spot // step) * step

    for s in strikes:
        dist = abs(spot - s)
        c_v = int(max(15000, 4_800_000 - (dist * 40000))) if s >= spot else int(5_500_000 - (dist * 25000))
        p_v = int(max(15000, 4_800_000 - (dist * 40000))) if s <= spot else int(5_500_000 - (dist * 25000))

        # Inject a deliberate secondary node so WTT/WTB vectors have something to detect
        if s == int(base_strike + step):
            c_v = int(c_v * 1.38)
        if s == int(base_strike - step):
            p_v = int(p_v * 1.15)

        c_v = max(c_v, 1)
        p_v = max(p_v, 1)

        records.append({
            "Strike": s,
            "Call_OI": int(c_v / 30),
            "Call_Vol": c_v,
            "Call_LTP": round(max(4.0, 140 - (s - spot) * 0.65) if s > spot else max(4.0, spot - s + 45), 2),
            "Put_LTP": round(max(4.0, 140 - (spot - s) * 0.65) if s < spot else max(4.0, s - spot + 45), 2),
            "Put_Vol": p_v,
            "Put_OI": int(p_v / 30),
        })

    return pd.DataFrame(records)


def get_option_chain(index_ticker: str, spot: float, step: int) -> pd.DataFrame:
    """
    Single entry point the dashboard calls every poll.
    Swap this body for a real DhanHQ API call when going live —
    the rest of the app never needs to change.
    """
    return generate_simulated_chain(spot, step)
