from __future__ import annotations

import sqlite3

from dashboard.research_notebook_view import (
    build_experiment_cards,
    build_experiment_timeline,
    build_notebook_workspace,
)
from src.api.research_notebook import ResearchNotebookApiV1
from src.persistence.research_notebook_repository import ResearchNotebookRepository
from src.research_notebook.service import ResearchNotebookService


def _service() -> ResearchNotebookService:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return ResearchNotebookService(ResearchNotebookRepository(connection))


def _experiment(service: ResearchNotebookService):
    return service.create_experiment(
        title="Plan A expectancy",
        hypothesis="Plan A has positive expectancy.",
        objective="Test whether validated Plan A trades retain positive expectancy.",
        planning_horizons=("NEXT_SESSION",),
        instruments=("NIFTY",),
        scenarios=("S1",),
        minimum_sample_size=2,
        primary_metric="expectancy_r",
        success_thresholds={"expectancy_r": {"operator": ">=", "value": 0.5}},
    )


def _evidence(outcome: str, r_value: float, suffix: str) -> dict:
    return {
        "evidence_id": f"ev-{suffix}",
        "trade_id": f"trade-{suffix}",
        "instrument": "NIFTY",
        "planning_horizon": "NEXT_SESSION",
        "scenario": "S1",
        "outcome": outcome,
        "realized_pnl": r_value * 1000.0,
        "realized_r_multiple": r_value,
        "mfe": max(r_value, 0.0) * 1000.0,
        "mae": min(r_value, 0.0) * 1000.0,
        "holding_seconds": 1800.0,
        "selected_plan": "A",
    }


def test_create_and_retrieve_experiment():
    service = _service()
    experiment = _experiment(service)
    detail = service.get_experiment(experiment.experiment_id)
    assert detail is not None
    assert detail["experiment"]["title"] == "Plan A expectancy"
    assert detail["mode"] == "SHADOW_RESEARCH_ONLY"


def test_supported_experiment_run_is_persisted():
    service = _service()
    experiment = _experiment(service)
    result = service.execute_experiment(
        experiment.experiment_id,
        [_evidence("WIN", 1.0, "1"), _evidence("WIN", 0.8, "2")],
    )
    assert result["run"]["status"] == "COMPLETED"
    assert result["conclusion"]["conclusion"] == "SUPPORTED"
    detail = service.get_experiment(experiment.experiment_id)
    assert len(detail["runs"]) == 1
    assert len(detail["conclusions"]) == 1


def test_insufficient_sample_is_inconclusive():
    service = _service()
    experiment = _experiment(service)
    result = service.execute_experiment(
        experiment.experiment_id,
        [_evidence("WIN", 1.0, "1")],
    )
    assert result["conclusion"]["conclusion"] == "INCONCLUSIVE"
    assert result["conclusion"]["governance_recommendation"] == "COLLECT_MORE_EVIDENCE"


def test_observation_and_api_detail():
    service = _service()
    experiment = _experiment(service)
    service.add_observation(
        experiment_id=experiment.experiment_id,
        title="Initial note",
        body="Sample is still small.",
        observation_type="NOTE",
    )
    api = ResearchNotebookApiV1(service)
    response = api.get_experiment(experiment.experiment_id)
    assert response["status"] == 200
    assert len(response["data"]["observations"]) == 1


def test_dashboard_read_models():
    service = _service()
    experiment = _experiment(service)
    service.execute_experiment(
        experiment.experiment_id,
        [_evidence("WIN", 1.0, "1"), _evidence("LOSS", -0.2, "2")],
    )
    detail = service.get_experiment(experiment.experiment_id)
    cards = build_experiment_cards(detail)
    timeline = build_experiment_timeline(detail)
    workspace = build_notebook_workspace(service.list_experiments())
    assert cards["runs"] == 1
    assert cards["conclusions"] == 1
    assert any(row["type"] == "CONCLUSION" for row in timeline)
    assert workspace["cards"]["total_experiments"] == 1
