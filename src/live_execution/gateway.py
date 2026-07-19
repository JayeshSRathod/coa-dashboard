"""Safety-first execution orchestration. This module owns all broker calls."""

from __future__ import annotations

from datetime import datetime
import logging
from time import sleep
from typing import Callable

from src.persistence.execution_repository import ExecutionRepository
from src.persistence.order_event_repository import OrderEventRepository
from src.persistence.order_repository import OrderRepository
from src.research.observability import emit_snapshot_event

from .brokers import BrokerAdapter
from .config import ExecutionConfig
from .models import ExecutionOrder, OrderEvent, OrderRequest
from .safety import validate_request


class ExecutionGateway:
    """Transform approved requests into event-sourced orders; no strategy code belongs here."""

    def __init__(
        self, config: ExecutionConfig, order_repository: OrderRepository,
        order_event_repository: OrderEventRepository, execution_repository: ExecutionRepository,
        adapters: dict[str, BrokerAdapter] | None = None, logger: logging.Logger | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.config = config
        self.order_repository = order_repository
        self.order_event_repository = order_event_repository
        self.execution_repository = execution_repository
        self.adapters = adapters or {}
        self.logger = logger or logging.getLogger("cqrp.execution_gateway")
        self.sleeper = sleeper

    def submit(self, request: OrderRequest, *, now: datetime | None = None) -> ExecutionOrder:
        existing = self.execution_repository.existing(request.client_order_key)
        if existing is not None:
            return existing
        order = self.order_repository.insert(ExecutionOrder.new(
            client_order_key=request.client_order_key, signal_id=request.signal_id, trade_id=request.trade_id,
            portfolio_id=request.portfolio_id, broker_name=request.broker_name,
            execution_mode=self.config.execution_mode, exchange=request.exchange, symbol=request.symbol,
            expiry=request.expiry, strike=request.strike, option_type=request.option_type,
            order_type=request.order_type, product_type=request.product_type,
            transaction_type=request.transaction_type, quantity=request.quantity, price=request.price,
            trigger_price=request.trigger_price, broker_order_id=None,
        ))
        self._event(order.order_id, "ORDER_CREATED", {"client_order_key": request.client_order_key})
        errors = validate_request(request, self.config, now=now)
        if errors:
            self._event(order.order_id, "ORDER_REJECTED", {"reason": "; ".join(errors)})
            emit_snapshot_event(self.logger, "execution_safety_rejected", order_id=order.order_id, reasons=errors)
            return order
        self._event(order.order_id, "ORDER_SUBMITTED", {"mode": self.config.execution_mode})
        if self.config.execution_mode in {"PAPER", "SIMULATION"}:
            self._event(order.order_id, "ORDER_ACKNOWLEDGED", {"broker_order_id": f"SIM-{order.order_id}"})
            self._event(order.order_id, "ORDER_FILLED", {
                "broker_order_id": f"SIM-{order.order_id}", "filled_quantity": order.quantity,
                "average_price": order.price,
            })
            return order
        adapter = self.adapters.get(request.broker_name)
        if adapter is None:
            self._event(order.order_id, "ORDER_REJECTED", {"reason": "broker adapter unavailable"})
            return order
        self._submit_live(order, request, adapter)
        return order

    def _submit_live(self, order: ExecutionOrder, request: OrderRequest, adapter: BrokerAdapter) -> None:
        for attempt in range(self.config.retry_attempts + 1):
            try:
                response = adapter.place_order(request)
                broker_order_id = response.get("id") or response.get("order_id") or response.get("broker_order_id")
                self._event(order.order_id, "ORDER_ACKNOWLEDGED", {
                    "broker_order_id": broker_order_id, "broker_response": response,
                })
                emit_snapshot_event(self.logger, "live_order_acknowledged", order_id=order.order_id,
                                    broker_name=adapter.name, attempt=attempt)
                return
            except (TimeoutError, ConnectionError) as exc:
                emit_snapshot_event(self.logger, "execution_retry", order_id=order.order_id, attempt=attempt,
                                    error=type(exc).__name__)
                if attempt < self.config.retry_attempts:
                    self.sleeper(0.1 * (attempt + 1))
                    continue
                self._event(order.order_id, "ORDER_REJECTED", {"reason": "broker network failure"})
            except Exception as exc:
                self._event(order.order_id, "ORDER_REJECTED", {"reason": f"broker error: {type(exc).__name__}"})
            return

    def _event(self, order_id: str, event_type: str, payload: dict) -> OrderEvent:
        event = self.order_event_repository.append(
            OrderEvent.new(order_id=order_id, event_type=event_type, payload=payload)
        )
        emit_snapshot_event(self.logger, "order_event", order_id=order_id, event_type=event_type)
        return event
