"""Immutable, replay-safe decision contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4
def _now() -> str: return datetime.now(timezone.utc).isoformat()
@dataclass(frozen=True)
class DecisionEvidence:
    category: str; result: str; score: float | None; detail: str; source_version: str
@dataclass(frozen=True)
class DecisionRejection:
    rule: str; severity: str; reason: str; timestamp: str = field(default_factory=_now)
@dataclass(frozen=True)
class TradeDecision:
    decision_id: str; snapshot_id: str; instrument: str; action: str; expiry: str | None; strike: float | None; option_type: str | None; entry: float | None; stop_loss: float | None; target_1: float | None; target_2: float | None; quantity: int; confidence: float; valid_until: str; status: str; rule_version: str; evidence: tuple[DecisionEvidence, ...] = (); rejections: tuple[DecisionRejection, ...] = (); metadata: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None: object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
    @classmethod
    def new(cls, **values: Any) -> "TradeDecision": values.setdefault("decision_id", str(uuid4())); return cls(**values)
