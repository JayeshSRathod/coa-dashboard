"""Read-only API facade for CQRP Research Notebook artifacts."""

from __future__ import annotations

from src.research_notebook.service import ResearchNotebookService


class ResearchNotebookApiV1:
    prefix = "/api/v1/research-notebook"

    def __init__(self, service: ResearchNotebookService) -> None:
        self.service = service

    def get_experiment(self, experiment_id: str) -> dict:
        detail = self.service.get_experiment(experiment_id)
        return {
            "status": 200 if detail else 404,
            "data": detail,
            "mode": "SHADOW_RESEARCH_ONLY",
        }

    def list_experiments(self, *, status: str | None = None, limit: int = 100) -> dict:
        rows = self.service.list_experiments(status=status, limit=limit)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_RESEARCH_ONLY",
        }
