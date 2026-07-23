from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
def now() -> str: return datetime.now(timezone.utc).isoformat()
@dataclass(frozen=True)
class PaperOrder:
    order_id: str; decision_id: str; instrument_id: str; side: str; quantity: int; order_type: str; limit_price: float | None; status: str; created_at: str
    @classmethod
    def new(cls, **values: object) -> "PaperOrder": values.setdefault("order_id", str(uuid4())); values.setdefault("status", "CREATED"); values.setdefault("created_at", now()); return cls(**values) # type: ignore[arg-type]
@dataclass(frozen=True)
class Position:
    position_id: str; order_id: str; instrument_id: str; quantity: int; entry_price: float; current_price: float; realized_pnl: float; status: str
    @property
    def unrealized_pnl(self) -> float: return round((self.current_price-self.entry_price)*self.quantity, 2)
