"""Append-only persistence for equity-curve points derived from an analytics report."""

from __future__ import annotations

import json

from src.analytics.models import PerformanceSnapshot

from .repository import SQLiteRepository


class PerformanceSnapshotRepository(SQLiteRepository):
    def append(self, snapshot: PerformanceSnapshot) -> PerformanceSnapshot:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO performance_snapshots (
                    performance_snapshot_id, report_id, portfolio_id, session_id, observed_at,
                    equity, drawdown, pnl, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot.performance_snapshot_id, snapshot.report_id, snapshot.portfolio_id,
                 snapshot.session_id, snapshot.observed_at, snapshot.equity, snapshot.drawdown,
                 snapshot.pnl, json.dumps(dict(snapshot.payload), sort_keys=True, separators=(",", ":"), default=str),
                 snapshot.created_at),
            )
        return snapshot

    def list_for_report(self, report_id: str) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT * FROM performance_snapshots WHERE report_id = ? "
            "ORDER BY observed_at ASC, performance_snapshot_id ASC", (report_id,)
        ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload_json"] or "{}")}
            for row in rows
        ]
