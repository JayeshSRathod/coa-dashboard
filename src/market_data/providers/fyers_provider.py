"""Fyers transport adapter; emits normalized CQRP models only."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

import requests

from ..contracts import OptionChainRequest
from ..mappers.fyers_mapper import map_fyers_option_chain
from ..models import MarketQuote, OptionChainSnapshot, ProviderHealth, QualityState


class FyersRequestError(RuntimeError):
    """A sanitized FYERS transport error that is safe to render to a user."""


class FyersProvider:
    name = "FYERS"

    def __init__(self, app_id: str, access_token: str, fetcher: Callable[[str, str, str, int], dict[str, Any]] | None = None) -> None:
        self.app_id, self.access_token = app_id, access_token
        self.fetcher = fetcher or self._fetch_raw
        self._last_health = ProviderHealth(self.name, _now(), QualityState.WARMING, None, 0, None)

    def fetch_option_chain(self, request: OptionChainRequest) -> OptionChainSnapshot:
        started = perf_counter()
        try:
            raw = self.fetcher(self.app_id, self.access_token, request.symbol, request.strike_count)
            snapshot = map_fyers_option_chain(raw, instrument_id=request.instrument_id, expiry=request.expiry, captured_at=_now(), latency_ms=(perf_counter() - started) * 1000)
            self._last_health = ProviderHealth(self.name, _now(), QualityState.HEALTHY, snapshot.latency_ms, 0, _now())
            return snapshot
        except Exception as exc:
            self._last_health = ProviderHealth(self.name, _now(), QualityState.OFFLINE, (perf_counter() - started) * 1000, self._last_health.error_count + 1, self._last_health.heartbeat_at, details={"error_type": type(exc).__name__})
            raise

    def fetch_quote(self, instrument_id: str, symbol: str) -> MarketQuote:
        snapshot = self.fetch_option_chain(OptionChainRequest(instrument_id, symbol, expiry=""))
        return MarketQuote(instrument_id, self.name, snapshot.spot, snapshot.captured_at, quality=snapshot.quality)

    def health(self) -> ProviderHealth:
        return self._last_health

    @staticmethod
    def _fetch_raw(app_id: str, access_token: str, symbol: str, strike_count: int) -> dict[str, Any]:
        # FYERS' current V3 SDK calls the data endpoint with a GET request,
        # query parameters, and an ``app_id:access_token`` header value.
        # Keeping this wire format aligned with the SDK avoids the legacy
        # endpoint's ``Invalid Request, please provide valid method`` error.
        try:
            http_response = requests.get(
                "https://api-t1.fyers.in/data/options-chain-v3",
                headers={"Authorization": f"{app_id}:{access_token}", "Content-Type": "application/json", "version": "3"},
                params={"symbol": symbol, "strikecount": strike_count, "timestamp": ""},
                timeout=20,
            )
            response = http_response.json()
        except requests.RequestException as exc:
            raise FyersRequestError("FYERS could not be reached. Check your internet connection and try again.") from exc
        except ValueError as exc:
            raise FyersRequestError("FYERS returned an invalid response. Try again shortly.") from exc
        if not isinstance(response, dict):
            raise FyersRequestError("FYERS returned an unexpected response.")
        if http_response.status_code >= 400 or response.get("s") != "ok":
            message = str(response.get("message") or f"HTTP {http_response.status_code}")
            raise FyersRequestError(f"FYERS option-chain request failed: {message}")
        data = response.get("data")
        if not isinstance(data, dict):
            raise FyersRequestError("FYERS returned no option-chain data for this instrument.")
        return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
