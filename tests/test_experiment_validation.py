from __future__ import annotations

import sqlite3

from dashboard.experiment_validation_view import build_validation_workspace
from src.api.experiment_validation import ExperimentValidationApiV1
from src.experiment_validation.engine import ExperimentValidationEngine
from src.experiment_validation.service import ExperimentValidationService
from src.pattern_discovery.models import PatternCandidate, PatternDefinition
from src.persistence.experiment_validation_repository import ExperimentValidationRepository


def _pattern() -> PatternCandidate:
    return PatternCandidate.new(
        title="Plan A pattern",
        description="Plan A shows superior win rate.",
        direction="POSITIVE",
        definition=PatternDefinition.new(
            feature_conditions={"selected_plan": "A"},
            outcome_target="WIN",
            comparison_group={"selected_plan": {"operator": "NOT_EQUALS", "value": "A"}},
        ),
        sample_size=20,
        comparison_sample_size=20,
        support_rate=70.0,
        baseline_rate=50.0,
        uplift=20.0,
        average_r_multiple=1.2,
        expectancy_r=1.2,
        confidence_score=80.0,
        stability_score=75.0,
        evidence_ids=tuple(f"discovery-{index}" for index in range(20)),
    )


def _evidence(count: int = 24, wins: int = 16):
    rows = []
    for index in range(count):
        is_win = index < wins
        rows.append({
            "evidence_id": f"validation-{index}",
            "trade_id": f"trade-{index}",
            "created_at": f"2026-08-{(index % 20) + 1:02d}T10:00:00+00:00",
            "selected_plan": "A",
            "instrument": "NIFTY",
            "planning_horizon": "INTRADAY",
            "regime": "TREND",
            "outcome": "WIN" if is_win else "LOSS",
            "realized_r_multiple": 1.5 if is_win else -1.0,
            "realized_pnl": 150.0 if is_win else -100.0,
            "feature_vector": {},
        })
    return rows


def test_engine_passes_robust_unseen_pattern():
    result = ExperimentValidationEngine(minimum_validation_sample=20).validate(_pattern(), _evidence())
    assert result.validation_sample_size == 24
    assert result.out_of_sample_win_rate > 60.0
    assert result.status in {"PASSED", "INCONCLUSIVE"}
    assert not set(result.evidence_ids).intersection(result.discovery_evidence_ids)


def test_engine_is_inconclusive_for_small_sample():
    result = ExperimentValidationEngine(minimum_validation_sample=20).validate(_pattern(), _evidence(count=8, wins=6))
    assert result.status == "INCONCLUSIVE"
    assert result.recommendation == "COLLECT_MORE_EVIDENCE"


def test_repository_service_api_and_workspace():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repository = ExperimentValidationRepository(connection)
    service = ExperimentValidationService(repository, ExperimentValidationEngine(minimum_validation_sample=10))
    result = service.validate(_pattern().as_dict(), _evidence(count=16, wins=11))

    assert repository.get(result.validation_id)["pattern_id"] == result.pattern_id
    assert service.latest_for_pattern(result.pattern_id)["validation_id"] == result.validation_id

    api = ExperimentValidationApiV1(service)
    response = api.get(result.validation_id)
    assert response["status"] == 200
    assert response["mode"] == "SHADOW_RESEARCH_ONLY"

    workspace = build_validation_workspace(service.list())
    assert workspace["cards"]["total_validations"] == 1
    assert workspace["rows"][0]["validation_id"] == result.validation_id
