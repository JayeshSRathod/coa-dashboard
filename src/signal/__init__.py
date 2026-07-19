"""Research-only deterministic signal domain; it has no execution capability."""

from .config import SignalConfig
from .engine import SignalEngine
from .models import ResearchSignal

__all__ = ["ResearchSignal", "SignalConfig", "SignalEngine"]
