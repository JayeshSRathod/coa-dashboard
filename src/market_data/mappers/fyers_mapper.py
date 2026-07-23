"""Fyers payload normalization. No CQRP decision logic belongs here."""

from __future__ import annotations

from typing import Any

from ..models import OptionChainSnapshot, OptionContract


def map_fyers_option_chain(raw: dict[str, Any], *, instrument_id: str, expiry: str, captured_at: str, latency_ms: float | None = None) -> OptionChainSnapshot:
    data = raw.get("data", raw)
    entries = data.get("optionsChain", [])
    spot = data.get("spot_price") or data.get("underlying_value")
    contracts: list[OptionContract] = []
    for entry in entries:
        option_type = str(entry.get("option_type") or "").upper()
        strike = entry.get("strike_price")
        if option_type not in ("CE", "PE") or strike in (None, 0):
            if spot is None:
                spot = entry.get("ltp")
            continue
        contracts.append(OptionContract(
            instrument_id=instrument_id, strike=float(strike), expiry=expiry, option_type=option_type,
            premium=float(entry.get("ltp") or 0), provider="FYERS", timestamp=captured_at,
            volume=_number(entry.get("volume")), oi=_number(entry.get("oi")),
            oi_change=_number(entry.get("oi_change") or entry.get("oich")), iv=_number(entry.get("iv")),
            bid=_number(entry.get("bid")), ask=_number(entry.get("ask")), greeks=_greeks(entry),
        ))
    if spot is None:
        raise ValueError("Fyers option-chain payload does not contain an underlying spot")
    return OptionChainSnapshot.new(instrument_id=instrument_id, spot=float(spot), expiry=expiry, provider="FYERS", captured_at=captured_at, contracts=contracts, latency_ms=latency_ms, metadata={"broker_payload_version": "fyers-optionchain-v1"})


def _number(value: Any) -> float | None:
    return None if value is None else float(value)


def _greeks(entry: dict[str, Any]) -> dict[str, float]:
    return {key: float(entry[key]) for key in ("delta", "gamma", "theta", "vega") if entry.get(key) is not None}
