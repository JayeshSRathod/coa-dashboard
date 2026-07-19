"""Pure order-event projector for deterministic lifecycle reconstruction."""

from __future__ import annotations

from collections.abc import Iterable

from .models import ExecutionOrder, OrderEvent, OrderState


def project_order(order: ExecutionOrder, events: Iterable[OrderEvent]) -> OrderState:
    status, broker_order_id, filled, average_price, rejection = "CREATED", order.broker_order_id, 0, None, None
    for event in events:
        payload = event.payload
        if event.event_type == "ORDER_SUBMITTED":
            status = "SUBMITTED"
        elif event.event_type == "ORDER_ACKNOWLEDGED":
            status, broker_order_id = "ACKNOWLEDGED", payload.get("broker_order_id", broker_order_id)
        elif event.event_type == "ORDER_PARTIALLY_FILLED":
            status, filled = "PARTIALLY_FILLED", int(payload.get("filled_quantity", filled))
            average_price = payload.get("average_price", average_price)
        elif event.event_type == "ORDER_FILLED":
            status, filled = "FILLED", int(payload.get("filled_quantity", order.quantity))
            average_price = payload.get("average_price", average_price)
        elif event.event_type == "ORDER_MODIFIED":
            status = "MODIFIED"
        elif event.event_type == "ORDER_CANCELLED":
            status = "CANCELLED"
        elif event.event_type == "ORDER_REJECTED":
            status, rejection = "REJECTED", payload.get("reason")
        elif event.event_type == "ORDER_EXPIRED":
            status = "EXPIRED"
    return OrderState(order_id=order.order_id, status=status, broker_order_id=broker_order_id,
                      filled_quantity=filled, pending_quantity=max(0, order.quantity - filled),
                      average_price=average_price, rejection_reason=rejection)
