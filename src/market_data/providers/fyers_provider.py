"""Fyers transport adapter; emits normalized CQRP models only."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

from ..contracts import OptionChainRequest
from ..mappers.fyers_mapper import map_fyers_option_chain
from ..models import MarketQuote, OptionChainSnapshot, ProviderHealth, QualityState


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
        from fyers_apiv3 import fyersModel
        client = fyersModel.FyersModel(client_id=app_id, token=access_token, is_async=False, log_path="")
        response = client.optionchain(data={"symbol": symbol, "strikecount": str(strike_count), "timestamp": ""})
        if response.get("s") != "ok":
            raise RuntimeError(f"Fyers option-chain request failed: {response.get('message', 'unknown error')}")
        return response.get("data", {})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
