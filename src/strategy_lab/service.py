"""Strategy-lab service APIs and deterministic experiment runner."""

from __future__ import annotations

from hashlib import sha256
import json
import logging
from time import perf_counter
from typing import Callable

from src.research.observability import emit_snapshot_event

from .comparison import compare_runs
from .models import Configuration, Dataset, Experiment, ExperimentRun, Strategy
from .promotion import evaluate_promotion


def _checksum(values: object) -> str:
    return sha256(json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class StrategyLabService:
    """Coordinates append-only repositories; actual pipeline execution is injected."""

    def __init__(
        self, strategy_repository, configuration_repository, dataset_repository,
        experiment_repository, promotion_repository, notebook_repository,
        logger: logging.Logger | None = None, knowledge_builder=None,
    ) -> None:
        self.strategies = strategy_repository
        self.configurations = configuration_repository
        self.datasets = dataset_repository
        self.experiments = experiment_repository
        self.promotions = promotion_repository
        self.notebook = notebook_repository
        self.logger = logger or logging.getLogger("cqrp.strategy_lab")
        self.knowledge_builder = knowledge_builder

    def create_strategy(self, **values) -> Strategy:
        strategy = self.strategies.insert(Strategy.new(**values))
        emit_snapshot_event(self.logger, "strategy_created", strategy_id=strategy.strategy_id)
        return strategy

    def clone_strategy(self, strategy_id: str, *, strategy_name: str, version: str,
                       status: str = "EXPERIMENTAL") -> Strategy:
        parent = self.strategies.get(strategy_id)
        if parent is None:
            raise ValueError("parent strategy not found")
        clone = self.create_strategy(
            strategy_name=strategy_name, description=parent.description, owner=parent.owner,
            category=parent.category, asset_class=parent.asset_class, market=parent.market,
            version=version, status=status, parent_strategy_id=parent.strategy_id,
        )
        for configuration in self.configurations.list_for_strategy(parent.strategy_id):
            self.create_configuration(clone.strategy_id, dict(configuration.values))
        emit_snapshot_event(self.logger, "strategy_cloned", strategy_id=clone.strategy_id,
                            parent_strategy_id=parent.strategy_id)
        return clone

    def create_configuration(self, strategy_id: str, values: dict) -> Configuration:
        configuration = self.configurations.insert(Configuration.new(
            strategy_id=strategy_id, values=values, checksum=_checksum(values)
        ))
        emit_snapshot_event(self.logger, "configuration_registered",
                            strategy_id=strategy_id, configuration_id=configuration.configuration_id)
        return configuration

    def register_dataset(self, **values) -> Dataset:
        payload = {key: values[key] for key in ("market", "source", "symbols", "from_date", "to_date", "snapshot_count")}
        dataset = self.datasets.insert(Dataset.new(**values, checksum=_checksum(payload)))
        emit_snapshot_event(self.logger, "dataset_registered", dataset_id=dataset.dataset_id)
        return dataset

    def create_experiment(self, **values) -> Experiment:
        experiment = self.experiments.insert(Experiment.new(**values))
        self.notebook.append(experiment_id=experiment.experiment_id, entry_type="CREATED", content={
            "configuration_id": experiment.configuration_id, "dataset_id": experiment.dataset_id,
            "hypothesis": experiment.hypothesis,
        })
        emit_snapshot_event(self.logger, "experiment_created", experiment_id=experiment.experiment_id,
                            strategy_id=experiment.strategy_id)
        return experiment

    def run_experiment(self, experiment_id: str, pipeline: Callable[[Experiment, Dataset, Configuration], dict]) -> ExperimentRun:
        experiment = self.experiments.get(experiment_id)
        if experiment is None:
            raise ValueError("experiment not found")
        dataset = self.datasets.get(experiment.dataset_id)
        configuration = self.configurations.get(experiment.configuration_id)
        if dataset is None or configuration is None:
            raise ValueError("experiment references unavailable immutable inputs")
        fingerprint = _checksum({
            "strategy_id": experiment.strategy_id, "dataset_checksum": dataset.checksum,
            "configuration_checksum": configuration.checksum, "execution_mode": experiment.execution_mode,
        })
        existing = self.experiments.list_runs([experiment_id])
        for run in existing:
            if run.input_fingerprint == fingerprint:
                return run
        started = perf_counter()
        emit_snapshot_event(self.logger, "experiment_started", experiment_id=experiment_id)
        try:
            # The injected pipeline is responsible for the existing replay -> COA -> validation ->
            # signal -> risk -> paper execution -> analytics sequence. This layer does not bypass it.
            results = dict(pipeline(experiment, dataset, configuration))
            run = ExperimentRun.new(experiment_id=experiment_id, input_fingerprint=fingerprint,
                                    status="COMPLETED", execution_time_ms=(perf_counter() - started) * 1000,
                                    results=results)
        except Exception as exc:
            run = ExperimentRun.new(experiment_id=experiment_id, input_fingerprint=fingerprint,
                                    status="FAILED", execution_time_ms=(perf_counter() - started) * 1000,
                                    results={"error_type": type(exc).__name__})
        stored = self.experiments.append_run(run)
        # Optional observability hook: omitted builders preserve Sprint-012 behavior.
        if stored.status == "COMPLETED" and self.knowledge_builder is not None:
            self.knowledge_builder.process_completed_experiment(
                experiment, stored, self.strategies.get(experiment.strategy_id), dataset
            )
        self.notebook.append(experiment_id=experiment_id, entry_type="RUN", content={
            "run_id": stored.run_id, "status": stored.status, "results": dict(stored.results),
        })
        emit_snapshot_event(self.logger, "experiment_completed", experiment_id=experiment_id,
                            run_id=stored.run_id, status=stored.status)
        return stored

    def compare_experiments(self, experiment_ids: list[str]) -> dict:
        return compare_runs(self.experiments.list_runs(experiment_ids))

    def evaluate_promotion(self, experiment_id: str, criteria: dict[str, float]) -> str:
        experiment = self.experiments.get(experiment_id)
        runs = self.experiments.list_runs([experiment_id])
        if experiment is None or not runs:
            raise ValueError("completed experiment required")
        evaluation = evaluate_promotion(runs[-1].results, criteria)
        promotion_id = self.promotions.append(
            strategy_id=experiment.strategy_id, experiment_id=experiment_id,
            recommendation=evaluation.recommendation, criteria=dict(evaluation.criteria),
            evidence=dict(evaluation.evidence), notes="manual approval required",
        )
        self.notebook.append(experiment_id=experiment_id, entry_type="PROMOTION_EVALUATION", content={
            "promotion_id": promotion_id, "recommendation": evaluation.recommendation,
            "failed_criteria": evaluation.failed_criteria,
        })
        emit_snapshot_event(self.logger, "promotion_evaluated", experiment_id=experiment_id,
                            recommendation=evaluation.recommendation)
        return promotion_id
