"""Append-only persistence boundary for execution order lifecycle events."""

from __future__ import annotations

import json
import sqlite3

from src.live_execution.models import OrderEvent

from .repository import SQLiteRepository


def _decode(row) -> OrderEvent:
    return OrderEvent.new(
        event_id=row["event_id"], order_id=row["order_id"], event_type=row["event_type"],
        occurred_at=row["occurred_at"], payload=json.loads(row["payload_json"]),
        created_at=row["created_at"], created_by=row["created_by"],
    )


class OrderEventRepository(SQLiteRepository):
    def append(self, event: OrderEvent) -> OrderEvent:
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO order_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (event.event_id, event.order_id, event.event_type, event.occurred_at,
                     json.dumps(dict(event.payload), sort_keys=True, separators=(",", ":"), default=str),
                     event.created_at, event.created_by),
                )
        except sqlite3.IntegrityError:
            row = self.connection.execute(
                "SELECT * FROM order_events WHERE order_id = ? AND event_type = ? AND occurred_at = ?",
                (event.order_id, event.event_type, event.occurred_at),
            ).fetchone()
            if row:
                return _decode(row)
            raise
        return event

    def list_for_order(self, order_id: str) -> list[OrderEvent]:
        rows = self.connection.execute(
            "SELECT * FROM order_events WHERE order_id = ? ORDER BY occurred_at ASC, event_id ASC", (order_id,)
        ).fetchall()
        return [_decode(row) for row in rows]
