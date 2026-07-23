"""Append-only trade-decision persistence boundary."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from src.decision.models import TradeDecision
from .repository import SQLiteRepository
def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _json(value: object) -> str: return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
class DecisionRepository(SQLiteRepository):
    def append(self, decision: TradeDecision) -> TradeDecision:
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO trade_decision VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (decision.decision_id, decision.snapshot_id, decision.action, decision.status, decision.confidence, decision.valid_until, _json(decision), _now()))
            for evidence in decision.evidence: self.connection.execute("INSERT OR IGNORE INTO decision_evidence VALUES (?, ?, ?, ?, ?)", (str(uuid4()), decision.decision_id, evidence.category, _json(evidence), _now()))
            for rejection in decision.rejections: self.connection.execute("INSERT OR IGNORE INTO decision_rejection VALUES (?, ?, ?, ?, ?, ?)", (str(uuid4()), decision.decision_id, rejection.rule, rejection.severity, _json(rejection), _now()))
            self.connection.execute("INSERT OR IGNORE INTO decision_lifecycle VALUES (?, ?, ?, ?, ?, ?)", (str(uuid4()), decision.decision_id, None, decision.status, _now(), "{}"))
        return decision
