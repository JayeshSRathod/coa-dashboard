"""Deterministic in-process event bus; transport adapters subscribe externally."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
@dataclass(frozen=True)
class CQRPEvent:
    event_type: str; payload: Mapping[str, Any]; occurred_at: str
    @classmethod
    def new(cls, event_type: str, payload: Mapping[str, Any]) -> "CQRPEvent": return cls(event_type, dict(payload), datetime.now(timezone.utc).isoformat())
class InMemoryEventBus:
    def __init__(self) -> None: self._handlers: dict[str, list[Callable[[CQRPEvent], None]]] = {}; self.events: list[CQRPEvent] = []
    def subscribe(self, event_type: str, handler: Callable[[CQRPEvent], None]) -> None: self._handlers.setdefault(event_type, []).append(handler)
    def publish(self, event: CQRPEvent) -> None:
        self.events.append(event)
        for handler in self._handlers.get(event.event_type, ()): handler(event)
