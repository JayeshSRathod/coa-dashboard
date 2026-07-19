"""Configuration contract for safety-first execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

_ALLOWED_MODES = {"PAPER", "LIVE", "SIMULATION", "DISABLED"}


@dataclass(frozen=True)
class ExecutionConfig:
    execution_mode: str = "DISABLED"
    default_broker: str = "fyers"
    trading_enabled: bool = False
    kill_switch: bool = True
    emergency_stop: bool = False
    dry_run: bool = True
    max_order_quantity: int = 500
    max_order_value: float = 200_000.0
    trading_start: time = time(9, 15)
    trading_end: time = time(15, 25)
    retry_attempts: int = 2

    def __post_init__(self) -> None:
        if self.execution_mode not in _ALLOWED_MODES:
            raise ValueError(f"unsupported execution mode: {self.execution_mode}")
        if self.max_order_quantity < 1 or self.max_order_value <= 0:
            raise ValueError("order limits must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts cannot be negative")
