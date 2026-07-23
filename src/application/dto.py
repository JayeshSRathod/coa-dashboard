"""Serializable public DTOs; domain types never cross this boundary."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from src.decision.models import TradeDecision
@dataclass(frozen=True)
class DecisionDTO:
    decision_id: str; snapshot_id: str; instrument: str; action: str; expiry: str | None; strike: float | None; entry: float | None; stop_loss: float | None; target_1: float | None; target_2: float | None; quantity: int; confidence: float; valid_until: str; status: str; execution_mode: str
    @classmethod
    def from_domain(cls, decision: TradeDecision) -> "DecisionDTO": return cls(decision.decision_id, decision.snapshot_id, decision.instrument, decision.action, decision.expiry, decision.strike, decision.entry, decision.stop_loss, decision.target_1, decision.target_2, decision.quantity, decision.confidence, decision.valid_until, decision.status, str(decision.metadata.get("execution_mode", "DISABLED")))
    def to_dict(self) -> dict[str, object]: return asdict(self)
