"""Pure safety validation performed before an execution gateway contacts a broker."""

from __future__ import annotations

from datetime import datetime

from .config import ExecutionConfig
from .models import OrderRequest


def validate_request(
    request: OrderRequest, config: ExecutionConfig, *, now: datetime | None = None
) -> list[str]:
    errors: list[str] = []
    value = request.estimated_value or (request.price or 0.0) * request.quantity
    if config.execution_mode == "DISABLED":
        errors.append("execution mode is disabled")
    if request.quantity > config.max_order_quantity:
        errors.append("maximum order quantity exceeded")
    if value > config.max_order_value:
        errors.append("maximum order value exceeded")
    if not request.symbol or not request.exchange:
        errors.append("instrument is unavailable")
    if not request.approval_reference:
        errors.append("portfolio approval reference is required")
    if config.execution_mode == "LIVE":
        if not config.trading_enabled:
            errors.append("live trading is not enabled")
        if config.kill_switch:
            errors.append("kill switch is active")
        if config.emergency_stop:
            errors.append("emergency stop is active")
        if config.dry_run:
            errors.append("dry-run mode blocks live orders")
        local_time = (now or datetime.now()).time()
        if not config.trading_start <= local_time <= config.trading_end:
            errors.append("outside configured trading hours")
    return errors
