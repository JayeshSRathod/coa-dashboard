"""Append-only persistence boundary for reproducible analytics reports."""

from __future__ import annotations

import json
import sqlite3

from src.analytics.models import AnalyticsReport

from .repository import SQLiteRepository


def _decode(row: sqlite3.Row) -> AnalyticsReport:
    return AnalyticsReport.new(
        report_id=row["report_id"], report_type=row["report_type"],
        analytics_version=row["analytics_version"], scope=json.loads(row["scope_json"]),
        source_fingerprint=row["source_fingerprint"], metrics=json.loads(row["metrics_json"]),
        groups=json.loads(row["groups_json"]), created_at=row["created_at"],
        created_by=row["created_by"],
    )


class ReportRepository(SQLiteRepository):
    """Store report artifacts, never mutable cache records."""

    def append(self, report: AnalyticsReport) -> AnalyticsReport:
        existing = self.get_by_fingerprint(
            report.report_type, report.analytics_version, report.source_fingerprint
        )
        if existing is not None:
            return existing
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO analytics_reports (
                        report_id, report_type, analytics_version, scope_json, source_fingerprint,
                        metrics_json, groups_json, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (report.report_id, report.report_type, report.analytics_version,
                     json.dumps(dict(report.scope), sort_keys=True, separators=(",", ":"), default=str),
                     report.source_fingerprint,
                     json.dumps(dict(report.metrics), sort_keys=True, separators=(",", ":"), default=str),
                     json.dumps(dict(report.groups), sort_keys=True, separators=(",", ":"), default=str),
                     report.created_at, report.created_by),
                )
        except sqlite3.IntegrityError:
            existing = self.get_by_fingerprint(
                report.report_type, report.analytics_version, report.source_fingerprint
            )
            if existing is not None:
                return existing
            raise
        return report

    def get(self, report_id: str) -> AnalyticsReport | None:
        row = self.connection.execute(
            "SELECT * FROM analytics_reports WHERE report_id = ?", (report_id,)
        ).fetchone()
        return _decode(row) if row else None

    def get_by_fingerprint(
        self, report_type: str, analytics_version: str, source_fingerprint: str
    ) -> AnalyticsReport | None:
        row = self.connection.execute(
            "SELECT * FROM analytics_reports WHERE report_type = ? AND analytics_version = ? "
            "AND source_fingerprint = ?", (report_type, analytics_version, source_fingerprint)
        ).fetchone()
        return _decode(row) if row else None
