"""Dhan payload normalization. No CQRP decision logic belongs here."""

from __future__ import annotations

from typing import Any

from ..models import OptionChainSnapshot, OptionContract


def map_dhan_option_chain(raw: dict[str, Any], *, instrument_id: str, expiry: str, captured_at: str, latency_ms: float | None = None) -> OptionChainSnapshot:
    data = raw.get("data", raw)
    spot = data.get("last_price") or data.get("underlying_price")
    if spot is None:
        raise ValueError("Dhan option-chain payload does not contain last_price")
    contracts: list[OptionContract] = []
    for strike_text, sides in (data.get("oc") or {}).items():
        for option_type, key in (("CE", "ce"), ("PE", "pe")):
            side = (sides or {}).get(key) or {}
            contracts.append(OptionContract(
                instrument_id=instrument_id, strike=float(strike_text), expiry=expiry, option_type=option_type,
                premium=float(side.get("last_price") or 0), provider="DHAN", timestamp=captured_at,
                volume=_number(side.get("volume")), oi=_number(side.get("oi")),
                oi_change=_number(side.get("oi_change") or side.get("oiChange")), iv=_number(side.get("iv")),
                bid=_number(side.get("bid_price") or side.get("bid")), ask=_number(side.get("ask_price") or side.get("ask")),
                greeks=_greeks(side),
            ))
    return OptionChainSnapshot.new(instrument_id=instrument_id, spot=float(spot), expiry=expiry, provider="DHAN", captured_at=captured_at, contracts=contracts, latency_ms=latency_ms, metadata={"broker_payload_version": "dhan-optionchain-v1"})


def _number(value: Any) -> float | None:
    return None if value is None else float(value)


def _greeks(entry: dict[str, Any]) -> dict[str, float]:
    return {key: float(entry[key]) for key in ("delta", "gamma", "theta", "vega") if entry.get(key) is not None}
