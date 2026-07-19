"""Stable CSV and JSON export adapters for immutable analytics reports."""

from __future__ import annotations

import csv
import io
import json

from .models import AnalyticsReport


def report_json(report: AnalyticsReport) -> str:
    return json.dumps(
        {"report_id": report.report_id, "report_type": report.report_type,
         "analytics_version": report.analytics_version, "scope": dict(report.scope),
         "source_fingerprint": report.source_fingerprint, "metrics": dict(report.metrics),
         "groups": dict(report.groups), "created_at": report.created_at},
        sort_keys=True, separators=(",", ":"), default=str,
    )


def report_csv(report: AnalyticsReport) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["section", "key", "value"])
    for key, value in sorted(report.metrics.items()):
        writer.writerow(["metrics", key, value])
    for group, values in sorted(report.groups.items()):
        for key, value in sorted(dict(values).items()):
            writer.writerow([f"group:{group}", key, value])
    return stream.getvalue()
