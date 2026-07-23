"""Versioned read facade. A web framework may adapt these serializable responses."""
from __future__ import annotations
from typing import Any
from src.application.services import DecisionService
class CQRPApiV1:
    prefix = "/api/v1"
    def __init__(self, decisions: DecisionService) -> None: self.decisions = decisions
    def get_decision(self, decision_id: str) -> dict[str, Any]:
        decision = self.decisions.get(decision_id)
        return {"status": 200, "data": decision.to_dict()} if decision else {"status": 404, "error": "decision not found"}
    def get_decisions(self) -> dict[str, Any]: return {"status": 200, "data": [item.to_dict() for item in self.decisions.list()]}
    def get_system(self) -> dict[str, Any]: return {"status": 200, "data": {"api_version": "v1", "execution_mode": "DISABLED", "event_count": len(self.decisions.event_bus.events)}}
