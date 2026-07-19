"""Structured, deterministic research reports and export encoders."""

from __future__ import annotations

import csv
from hashlib import sha256
from io import StringIO
import json

from .models import KnowledgeReport


class ResearchReportGenerator:
    def __init__(self, query_engine, report_repository, logger=None) -> None:
        self.query_engine = query_engine
        self.reports = report_repository
        self.logger = logger

    def generate(self, report_type: str, *, scope: str = "GLOBAL", scope_key: str = "ALL") -> KnowledgeReport:
        payload = {
            "research_summary": self.query_engine.get_research_summary(),
            "best_strategy": self.query_engine.find_best_strategy(),
            "best_instrument": self.query_engine.find_best_instrument(),
            "best_market": self.query_engine.find_best_market(),
            "best_scenario": self.query_engine.find_best_scenario(),
        }
        fingerprint = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        report = self.reports.append(KnowledgeReport.new(
            report_type=report_type, scope=scope, scope_key=scope_key,
            fingerprint=fingerprint, payload=payload,
        ))
        if self.logger:
            self.logger.info({"event": "knowledge_report_generated", "report_id": report.report_id,
                              "report_type": report_type})
        return report

    @staticmethod
    def export(report: KnowledgeReport, format: str) -> str:
        if format.upper() == "JSON":
            return json.dumps(dict(report.payload), sort_keys=True, default=str)
        if format.upper() == "CSV":
            stream = StringIO()
            writer = csv.writer(stream)
            writer.writerow(["section", "value"])
            for key, value in sorted(report.payload.items()):
                writer.writerow([key, json.dumps(value, sort_keys=True, default=str)])
            return stream.getvalue()
        raise ValueError("supported deterministic formats are JSON and CSV; PDF/Excel are future adapters")
