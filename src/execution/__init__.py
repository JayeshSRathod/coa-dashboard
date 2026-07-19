"""Deterministic event-sourced paper execution; no broker integration."""

from .config import PaperExecutionConfig
from .engine import PaperExecutionEngine
from .models import PaperTrade, TradeEvent, TradeState

__all__ = ["PaperExecutionConfig", "PaperExecutionEngine", "PaperTrade", "TradeEvent", "TradeState"]
