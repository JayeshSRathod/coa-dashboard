"""Append-only repositories for deterministic CQRP research knowledge."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.knowledge.models import KnowledgeFact, KnowledgeReport
from .repository import SQLiteRepository


def _normalise(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalise(item) for item in value]
    return value


def _json(value: Any) -> str:
    return json.dumps(_normalise(value), default=str, sort_keys=True, separators=(",", ":"))


def _fact(row) -> KnowledgeFact:
    return KnowledgeFact.new(
        fact_id=row["fact_id"], source_run_id=row["source_run_id"], domain=row["domain"],
        subject_type=row["subject_type"], subject_key=row["subject_key"],
        strategy_id=row["strategy_id"], experiment_id=row["experiment_id"], market=row["market"],
        metrics=json.loads(row["metrics_json"]), summary=json.loads(row["summary_json"]),
        occurred_at=row["occurred_at"], created_by=row["created_by"],
    )


class KnowledgeRepository(SQLiteRepository):
    def append(self, fact: KnowledgeFact) -> KnowledgeFact:
        row = self.connection.execute(
            """SELECT * FROM knowledge_facts WHERE source_run_id=? AND domain=?
               AND subject_type=? AND subject_key=?""",
            (fact.source_run_id, fact.domain, fact.subject_type, fact.subject_key),
        ).fetchone()
        if row:
            return _fact(row)
        with self.connection:
            self.connection.execute(
                "INSERT INTO knowledge_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fact.fact_id, fact.source_run_id, fact.domain, fact.subject_type, fact.subject_key,
                 fact.strategy_id, fact.experiment_id, fact.market, _json(fact.metrics),
                 _json(fact.summary), fact.occurred_at, fact.created_by),
            )
        return fact

    def list(self, *, domain: str | None = None, subject_type: str | None = None,
             subject_key: str | None = None, market: str | None = None) -> list[KnowledgeFact]:
        clauses, values = [], []
        for name, value in (("domain", domain), ("subject_type", subject_type),
                            ("subject_key", subject_key), ("market", market)):
            if value is not None:
                clauses.append(f"{name}=?"); values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            "SELECT * FROM knowledge_facts" + where + " ORDER BY occurred_at, fact_id", values
        ).fetchall()
        return [_fact(row) for row in rows]


class StrategyKnowledgeRepository(KnowledgeRepository):
    def list(self, **filters):
        filters.setdefault("domain", "STRATEGY")
        return super().list(**filters)


class ScenarioKnowledgeRepository(KnowledgeRepository):
    def list(self, **filters):
        filters.setdefault("domain", "SCENARIO")
        return super().list(**filters)


class InstrumentKnowledgeRepository(KnowledgeRepository):
    def list(self, **filters):
        filters.setdefault("domain", "INSTRUMENT")
        return super().list(**filters)


class ExperimentKnowledgeRepository(KnowledgeRepository):
    def list(self, **filters):
        filters.setdefault("domain", "EXPERIMENT")
        return super().list(**filters)


class MarketKnowledgeRepository(KnowledgeRepository):
    def list(self, **filters):
        filters.setdefault("domain", "MARKET")
        return super().list(**filters)


class KnowledgeReportRepository(SQLiteRepository):
    def append(self, report: KnowledgeReport) -> KnowledgeReport:
        row = self.connection.execute(
            "SELECT * FROM knowledge_reports WHERE fingerprint=?", (report.fingerprint,)
        ).fetchone()
        if row:
            return KnowledgeReport.new(
                report_id=row["report_id"], report_type=row["report_type"], scope=row["scope"],
                scope_key=row["scope_key"], fingerprint=row["fingerprint"],
                payload=json.loads(row["payload_json"]), generated_at=row["generated_at"],
                created_by=row["created_by"],
            )
        with self.connection:
            self.connection.execute(
                "INSERT INTO knowledge_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (report.report_id, report.report_type, report.scope, report.scope_key,
                 report.fingerprint, _json(report.payload), report.generated_at, report.created_by),
            )
        return report
