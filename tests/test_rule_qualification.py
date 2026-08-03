from __future__ import annotations

import sqlite3

from dashboard.rule_qualification_view import build_rule_qualification_cards
from src.api.rule_qualification import RuleQualificationApiV1
from src.experiment_validation.models import ValidationResult
from src.pattern_discovery.models import PatternCandidate, PatternDefinition
from src.persistence.rule_qualification_repository import RuleQualificationRepository
from src.rule_qualification.engine import RuleQualificationEngine
from src.rule_qualification.service import RuleQualificationService


def _pattern() -> PatternCandidate:
    return PatternCandidate.new(
        pattern_id="pattern-1",
        title="Plan A next-session pattern",
        description="Synthetic qualified pattern",
        definition=PatternDefinition.new(
            feature_conditions={"selected_plan": "A"},
            outcome_target="WIN",
            planning_horizons=("NEXT_SESSION",),
        ),
        sample_size=40,
        comparison_sample_size=40,
        support_rate=68.0,
        baseline_rate=52.0,
        uplift=16.0,
        confidence_score=82.0,
        stability_score=78.0,
        evidence_ids=tuple(f"d-{index}" for index in range(40)),
    )


def _validation(*, passed: bool = True) -> ValidationResult:
    return ValidationResult.new(
        validation_id="validation-1",
        pattern_id="pattern-1",
        status="PASSED" if passed else "FAILED",
        recommendation="ELIGIBLE_FOR_RULE_QUALIFICATION" if passed else "REJECT_PATTERN",
        validation_score=86.0 if passed else 35.0,
        discovery_sample_size=40,
        validation_sample_size=30,
        in_sample_win_rate=68.0,
        out_of_sample_win_rate=64.0 if passed else 40.0,
        stability_score=80.0 if passed else 35.0,
        walk_forward_score=75.0,
        bootstrap_score=70.0,
        monte_carlo_score=72.0,
        drift_score=78.0,
        sensitivity_score=66.0,
    )


def test_engine_qualifies_passed_pattern() -> None:
    result = RuleQualificationEngine().qualify(_pattern(), _validation())
    assert result.status == "QUALIFIED"
    assert result.recommendation == "PROMOTE_TO_SHADOW_RULE"
    assert result.definition.execution_constraints["mode"] == "SHADOW_ONLY"
    assert result.definition.execution_constraints["live_order_enabled"] is False


def test_engine_rejects_failed_validation() -> None:
    result = RuleQualificationEngine().qualify(_pattern(), _validation(passed=False))
    assert result.status == "REJECTED"
    assert "VALIDATION_NOT_PASSED" in result.failed_gates


def test_repository_service_api_and_dashboard() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repository = RuleQualificationRepository(connection)
    service = RuleQualificationService(repository)
    api = RuleQualificationApiV1(service)

    created = service.qualify(_pattern(), _validation())
    fetched = api.get(created["qualification_id"])
    listed = api.qualified()
    cards = build_rule_qualification_cards(listed["data"])

    assert fetched["status"] == 200
    assert fetched["data"]["rule_id"] == created["rule_id"]
    assert listed["count"] == 1
    assert cards["qualified"] == 1
    assert cards["mode"] == "SHADOW_RULE_ONLY"
