"""Read/write application services; presentation layers must depend on these only."""
from __future__ import annotations
from src.decision.models import TradeDecision
from .dto import DecisionDTO
from .events import CQRPEvent, InMemoryEventBus
class DecisionService:
    def __init__(self, event_bus: InMemoryEventBus | None = None) -> None: self.event_bus = event_bus or InMemoryEventBus(); self._decisions: dict[str, DecisionDTO] = {}
    def publish_decision(self, decision: TradeDecision) -> DecisionDTO:
        dto = DecisionDTO.from_domain(decision); self._decisions[dto.decision_id] = dto; self.event_bus.publish(CQRPEvent.new("DecisionCreated", dto.to_dict())); return dto
    def get(self, decision_id: str) -> DecisionDTO | None: return self._decisions.get(decision_id)
    def list(self) -> list[DecisionDTO]: return list(self._decisions.values())
