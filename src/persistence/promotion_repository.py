"""Append-only promotion evidence and manual decision repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4
from .repository import SQLiteRepository


class PromotionRepository(SQLiteRepository):
    def append(self, *, strategy_id, experiment_id, recommendation, criteria, evidence,
               decision=None, notes=None, promotion_id=None):
        promotion_id = promotion_id or str(uuid4())
        with self.connection:
            self.connection.execute("INSERT INTO promotion_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (promotion_id, strategy_id, experiment_id, recommendation,
                 json.dumps(criteria, sort_keys=True), json.dumps(evidence, sort_keys=True),
                 decision, notes, datetime.now(timezone.utc).isoformat(), "StrategyLab"))
        return promotion_id
