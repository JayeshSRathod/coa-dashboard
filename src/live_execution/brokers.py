"""Broker contracts and adapters. No strategy or repository dependencies are allowed here."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from .models import OrderRequest


class BrokerAdapter(ABC):
    name: str

    @abstractmethod
    def place_order(self, request: OrderRequest) -> dict[str, Any]: ...

    @abstractmethod
    def modify_order(self, broker_order_id: str, changes: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def get_order(self, broker_order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_holdings(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_funds(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_trades(self) -> list[dict[str, Any]]: ...


class UnsupportedBrokerAdapter(BrokerAdapter):
    def __init__(self, name: str) -> None:
        self.name = name

    def _unsupported(self):
        raise NotImplementedError(f"{self.name} adapter is a Sprint-010 contract only")

    def place_order(self, request): return self._unsupported()
    def modify_order(self, broker_order_id, changes): return self._unsupported()
    def cancel_order(self, broker_order_id): return self._unsupported()
    def get_order(self, broker_order_id): return self._unsupported()
    def get_positions(self): return self._unsupported()
    def get_holdings(self): return self._unsupported()
    def get_funds(self): return self._unsupported()
    def get_trades(self): return self._unsupported()


class DhanBrokerAdapter(UnsupportedBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("dhan")


class ZerodhaBrokerAdapter(UnsupportedBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("zerodha")


class FyersBrokerAdapter(BrokerAdapter):
    """Thin Fyers adapter; credentials are injected and never persisted or logged."""

    name = "fyers"

    def __init__(self, app_id: str, access_token: str | None = None,
                 token_provider: Callable[[], str] | None = None) -> None:
        self.app_id = app_id
        self._access_token = access_token
        self._token_provider = token_provider

    @classmethod
    def with_refresh_token(
        cls, app_id: str, secret_key: str, refresh_token: str, pin: str
    ) -> "FyersBrokerAdapter":
        # Uses the existing isolated authentication utility; no secret is stored by CQRP.
        from engine.fyers_auth import refresh_fyers_access_token
        return cls(app_id, token_provider=lambda: refresh_fyers_access_token(
            app_id, secret_key, refresh_token, pin
        ))

    def _client(self):
        token = self._access_token or (self._token_provider() if self._token_provider else None)
        if not token:
            raise RuntimeError("Fyers access token is required")
        from fyers_apiv3 import fyersModel
        return fyersModel.FyersModel(client_id=self.app_id, token=token, is_async=False, log_path="")

    def place_order(self, request: OrderRequest) -> dict[str, Any]:
        payload = {
            "symbol": request.symbol, "qty": request.quantity,
            "type": 2 if request.order_type == "MARKET" else 1,
            "side": 1 if request.transaction_type == "BUY" else -1,
            "productType": request.product_type, "limitPrice": request.price or 0,
            "stopPrice": request.trigger_price or 0, "validity": "DAY",
        }
        return self._client().place_order(data=payload)

    def modify_order(self, broker_order_id, changes):
        return self._client().modify_order(data={"id": broker_order_id, **changes})

    def cancel_order(self, broker_order_id):
        return self._client().cancel_order(data={"id": broker_order_id})

    def get_order(self, broker_order_id):
        return self._client().orderbook(data={"id": broker_order_id})

    def get_positions(self):
        return self._client().positions().get("netPositions", [])

    def get_holdings(self):
        return self._client().holdings().get("holdings", [])

    def get_funds(self):
        return self._client().funds()

    def get_trades(self):
        return self._client().tradebook().get("tradeBook", [])
