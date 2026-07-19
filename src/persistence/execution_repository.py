"""Read-model repository for execution-gateway duplicate and lifecycle lookup."""

from __future__ import annotations

from .order_event_repository import OrderEventRepository
from .order_repository import OrderRepository


class ExecutionRepository:
    def __init__(self, order_repository: OrderRepository, event_repository: OrderEventRepository) -> None:
        self.order_repository = order_repository
        self.event_repository = event_repository

    def existing(self, client_order_key: str):
        return self.order_repository.get_by_client_key(client_order_key)

    def lifecycle(self, order_id: str):
        return self.event_repository.list_for_order(order_id)
