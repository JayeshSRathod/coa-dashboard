"""Repository for immutable simulated-trade lifecycle events."""

from __future__ import annotations

import json
import sqlite3
from src.execution.models import TradeEvent
from .repository import SQLiteRepository


def _decode(row):
    return TradeEvent.new(event_id=row["event_id"], trade_id=row["trade_id"], session_id=row["session_id"],
        source_snapshot_id=row["source_snapshot_id"], event_type=row["event_type"], occurred_at=row["occurred_at"],
        payload=json.loads(row["event_payload_json"]), created_at=row["created_at"], created_by=row["created_by"])


class TradeEventRepository(SQLiteRepository):
    def append(self, event: TradeEvent) -> TradeEvent:
        existing=self.find(event.trade_id,event.event_type,event.source_snapshot_id)
        if existing:return existing
        try:
            with self.connection:
                self.connection.execute("INSERT INTO simulated_trade_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (event.event_id,event.trade_id,event.session_id,event.source_snapshot_id,event.event_type,
                     event.occurred_at,json.dumps(dict(event.payload),sort_keys=True),event.created_at,event.created_by))
        except sqlite3.IntegrityError:
            existing=self.find(event.trade_id,event.event_type,event.source_snapshot_id)
            if existing:return existing
            raise
        return event

    def find(self, trade_id,event_type,source_snapshot_id):
        if source_snapshot_id is None:
            row=self.connection.execute("SELECT * FROM simulated_trade_events WHERE trade_id=? AND event_type=? AND source_snapshot_id IS NULL",(trade_id,event_type)).fetchone()
        else:
            row=self.connection.execute("SELECT * FROM simulated_trade_events WHERE trade_id=? AND event_type=? AND source_snapshot_id=?",(trade_id,event_type,source_snapshot_id)).fetchone()
        return _decode(row) if row else None

    def get_events(self, trade_id):
        return [_decode(row) for row in self.connection.execute("SELECT * FROM simulated_trade_events WHERE trade_id=? ORDER BY occurred_at,event_id",(trade_id,)).fetchall()]

    def get_events_by_session(self,session_id):
        return [_decode(row) for row in self.connection.execute("SELECT * FROM simulated_trade_events WHERE session_id=? ORDER BY occurred_at,event_id",(session_id,)).fetchall()]
