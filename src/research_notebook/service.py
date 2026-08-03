"""Application service for CQRP Research Notebook artifacts and experiment runs."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.persistence.research_notebook_repository import ResearchNotebookRepository

from .models import (
    ResearchExperiment,
    ResearchObservation,
)
from .runner import ResearchExperimentRunner


class ResearchNotebookService:
    def __init__(
        self,
        repository: ResearchNotebookRepository,
        runner: ResearchExperimentRunner | None = None,
    ) -> None:
        self.repository = repository
        self.runner = runner or ResearchExperimentRunner()

    def create_experiment(self, **values: Any) -> ResearchExperiment:
        experiment = ResearchExperiment.new(**values)
        self.repository.append_experiment(experiment)
        return experiment

    def add_observation(self, **values: Any) -> ResearchObservation:
        observation = ResearchObservation.new(**values)
        if self.repository.get_experiment(observation.experiment_id) is None:
            raise ValueError("experiment not found")
        self.repository.append_observation(observation)
        return observation

    def execute_experiment(
        self,
        experiment_id: str,
        evidence_records: Iterable[Mapping[str, Any]],
        *,
        statistics_snapshot_id: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.repository.get_experiment(experiment_id)
        if record is None:
            raise ValueError("experiment not found")
        experiment = ResearchExperiment.new(**record)
        run, conclusion = self.runner.run(
            experiment,
            evidence_records,
            statistics_snapshot_id=statistics_snapshot_id,
            parameters=parameters,
        )
        self.repository.append_run(run)
        self.repository.append_conclusion(conclusion)
        return {
            "experiment": experiment.as_dict(),
            "run": run.as_dict(),
            "conclusion": conclusion.as_dict(),
            "mode": "SHADOW_RESEARCH_ONLY",
        }

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        detail = self.repository.experiment_detail(experiment_id)
        if detail is None:
            return None
        return {**detail, "mode": "SHADOW_RESEARCH_ONLY"}

    def list_experiments(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list_experiments(status=status, limit=limit)
