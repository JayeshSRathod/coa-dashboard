"""
Fyers Authentication
----------------------
Fyers access tokens expire daily (SEBI-mandated, same as other brokers).
Unlike a full re-login, Fyers supports refreshing via a refresh_token + PIN,
which this module automates — no daily browser step required after the
one-time initial setup.

SECURITY NOTE: this requires storing your trading PIN in secrets. That is a
materially more sensitive credential than an API token — it's what
authorizes trades. Only proceed with this if you're comfortable with that
trade-off; the alternative (paste a fresh access_token daily, generated
manually) avoids storing the PIN entirely.

The refresh endpoint below (POST /api/v3/validate-refresh-token) is
confirmed from Fyers developer community sources; Fyers' own docs pages
are a JS app that couldn't be fetched directly for this project, so this
carries slightly less certainty than a doc-verified endpoint. Test with the
debug view before relying on it.
"""

import hashlib
import requests

FYERS_REFRESH_URL = "https://api-t1.fyers.in/api/v3/validate-refresh-token"


def refresh_fyers_access_token(app_id: str, secret_key: str, refresh_token: str, pin: str) -> str:
    """
    Exchanges a refresh_token + PIN for a fresh access_token.
    Raises on failure — caller should catch and fall back gracefully.
    """
    app_id_hash = hashlib.sha256(f"{app_id}:{secret_key}".encode()).hexdigest()
    resp = requests.post(
        FYERS_REFRESH_URL,
        json={
            "grant_type": "refresh_token",
            "appIdHash": app_id_hash,
            "refresh_token": refresh_token,
            "pin": pin,
        },
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("s") != "ok" or "access_token" not in payload:
        raise RuntimeError(f"Fyers token refresh failed: {payload}")
    return payload["access_token"]


def is_fyers_configured() -> bool:
    try:
        import streamlit as st
        f = st.secrets["fyers"]
        required = ["app_id", "secret_key", "refresh_token", "pin"]
        return all(f.get(k) for k in required) and "your-fyers" not in str(f.get("app_id", ""))
    except Exception:
        return False
