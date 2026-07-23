"""Dhan transport adapter; emits normalized CQRP models only."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

import requests

from ..contracts import OptionChainRequest
from ..mappers.dhan_mapper import map_dhan_option_chain
from ..models import MarketQuote, OptionChainSnapshot, ProviderHealth, QualityState


class DhanProvider:
    name = "DHAN"
    base_url = "https://api.dhan.co/v2"

    def __init__(self, client_id: str, access_token: str, fetcher: Callable[[str, str, int, str, str], dict[str, Any]] | None = None) -> None:
        self.client_id, self.access_token = client_id, access_token
        self.fetcher = fetcher or self._fetch_raw
        self._last_health = ProviderHealth(self.name, _now(), QualityState.WARMING, None, 0, None)

    def fetch_option_chain(self, request: OptionChainRequest) -> OptionChainSnapshot:
        if request.security_id is None or request.segment is None:
            raise ValueError("Dhan option-chain requests require security_id and segment")
        started = perf_counter()
        try:
            raw = self.fetcher(self.client_id, self.access_token, request.security_id, request.segment, request.expiry)
            snapshot = map_dhan_option_chain(raw, instrument_id=request.instrument_id, expiry=request.expiry, captured_at=_now(), latency_ms=(perf_counter() - started) * 1000)
            self._last_health = ProviderHealth(self.name, _now(), QualityState.HEALTHY, snapshot.latency_ms, 0, _now())
            return snapshot
        except Exception as exc:
            self._last_health = ProviderHealth(self.name, _now(), QualityState.OFFLINE, (perf_counter() - started) * 1000, self._last_health.error_count + 1, self._last_health.heartbeat_at, details={"error_type": type(exc).__name__})
            raise

    def fetch_quote(self, instrument_id: str, symbol: str) -> MarketQuote:
        raise NotImplementedError("Dhan quote support is not configured in Sprint-019")

    def health(self) -> ProviderHealth:
        return self._last_health

    @classmethod
    def _fetch_raw(cls, client_id: str, access_token: str, security_id: int, segment: str, expiry: str) -> dict[str, Any]:
        response = requests.post(f"{cls.base_url}/optionchain", headers={"access-token": access_token, "client-id": client_id, "Content-Type": "application/json"}, json={"UnderlyingScrip": security_id, "UnderlyingSeg": segment, "Expiry": expiry}, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Dhan option-chain request failed: {payload.get('remarks', 'unknown error')}")
        return payload.get("data", {})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
