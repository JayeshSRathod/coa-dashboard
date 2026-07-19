"""Deterministic extraction of completed experiment results into knowledge facts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.research.observability import emit_snapshot_event

from .models import KnowledgeFact


def _metrics(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _entries(value: object) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(value, Mapping):
        return [(str(key), _metrics(item)) for key, item in sorted(value.items())]
    if isinstance(value, list):
        result = []
        for item in value:
            data = _metrics(item)
            key = data.get("name") or data.get("scenario") or data.get("instrument") or data.get("market")
            if key is not None:
                result.append((str(key), data))
        return result
    return []


class KnowledgeBuilder:
    """Converts immutable completed runs into immutable, deduplicated facts."""

    def __init__(self, repository, logger=None) -> None:
        self.repository = repository
        self.logger = logger

    def process_completed_experiment(self, experiment, run, strategy=None, dataset=None) -> list[KnowledgeFact]:
        if run.status != "COMPLETED":
            return []
        results = dict(run.results)
        base = dict(
            source_run_id=run.run_id, strategy_id=experiment.strategy_id,
            experiment_id=experiment.experiment_id, market=experiment.market,
            occurred_at=run.occurred_at,
        )
        facts = [
            KnowledgeFact.new(domain="STRATEGY", subject_type="STRATEGY",
                              subject_key=experiment.strategy_id, metrics=results,
                              summary={"strategy_name": getattr(strategy, "strategy_name", None),
                                       "version": getattr(strategy, "version", None)}, **base),
            KnowledgeFact.new(domain="EXPERIMENT", subject_type="EXPERIMENT",
                              subject_key=experiment.experiment_id, metrics=results,
                              summary={"name": experiment.experiment_name, "dataset_id": experiment.dataset_id,
                                       "configuration_id": experiment.configuration_id}, **base),
            KnowledgeFact.new(domain="MARKET", subject_type="MARKET", subject_key=experiment.market,
                              metrics=_metrics(results.get("market_metrics")) or results,
                              summary={"execution_mode": experiment.execution_mode}, **base),
            KnowledgeFact.new(domain="PORTFOLIO", subject_type="PORTFOLIO",
                              subject_key=str(results.get("portfolio_id", "default")),
                              metrics=_metrics(results.get("portfolio_metrics")) or results,
                              summary={}, **base),
            KnowledgeFact.new(domain="VALIDATION", subject_type="VALIDATION",
                              subject_key=str(results.get("validation_version", "default")),
                              metrics=_metrics(results.get("validation_metrics")) or results,
                              summary={}, **base),
        ]
        for symbol in experiment.symbols:
            facts.append(KnowledgeFact.new(
                domain="INSTRUMENT", subject_type="INSTRUMENT", subject_key=symbol,
                metrics=_metrics(results.get("instrument_metrics", {}).get(symbol)) or results,
                summary={"dataset_id": experiment.dataset_id}, **base))
        for scenario, metrics in _entries(results.get("scenario_metrics", results.get("scenarios"))):
            facts.append(KnowledgeFact.new(
                domain="SCENARIO", subject_type="SCENARIO", subject_key=scenario,
                metrics=metrics, summary={}, **base))
        stored = [self.repository.append(fact) for fact in facts]
        if self.logger:
            emit_snapshot_event(self.logger, "knowledge_extracted", experiment_id=experiment.experiment_id,
                                run_id=run.run_id, facts=len(stored))
        return stored
