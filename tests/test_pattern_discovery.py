from __future__ import annotations

from dashboard.pattern_discovery_view import (
    build_pattern_cards,
    build_pattern_detail_rows,
    build_pattern_workspace,
)
from src.api.pattern_discovery import PatternDiscoveryApiV1
from src.pattern_discovery.engine import PatternDiscoveryEngine


def _evidence(index: int, *, selected_plan: str, outcome: str, r_multiple: float) -> dict:
    return {
        "evidence_id": f"ev-{index}",
        "instrument": "NIFTY",
        "planning_horizon": "INTRADAY",
        "scenario": "GAP_UP",
        "selected_plan": selected_plan,
        "regime": "TRENDING",
        "direction": "BUY",
        "exit_reason": "TARGET" if outcome == "WIN" else "STOP",
        "outcome": outcome,
        "realized_r_multiple": r_multiple,
        "feature_vector": {"opening_strength": "HIGH" if selected_plan == "A" else "LOW"},
    }


def test_discovery_finds_high_uplift_plan():
    rows = []
    for index in range(20):
        rows.append(_evidence(index, selected_plan="A", outcome="WIN" if index < 18 else "LOSS", r_multiple=1.5 if index < 18 else -1.0))
    for index in range(20, 40):
        rows.append(_evidence(index, selected_plan="B", outcome="WIN" if index < 24 else "LOSS", r_multiple=1.0 if index < 24 else -1.0))

    engine = PatternDiscoveryEngine(
        minimum_sample_size=10,
        minimum_uplift_points=10.0,
        minimum_confidence_score=40.0,
    )
    candidates = engine.discover(rows, feature_keys=("selected_plan",))

    assert candidates
    top = candidates[0]
    assert top.definition.feature_conditions["selected_plan"] == "A"
    assert top.direction == "POSITIVE"
    assert top.sample_size == 20
    assert top.support_rate == 90.0
    assert top.uplift is not None and top.uplift > 50.0
    assert top.supporting_metrics["research_only"] is True


def test_discovery_returns_empty_below_minimum_sample():
    engine = PatternDiscoveryEngine(minimum_sample_size=10)
    assert engine.discover([_evidence(1, selected_plan="A", outcome="WIN", r_multiple=1.0)]) == ()


class _FakeService:
    def get(self, pattern_id):
        return {"pattern_id": pattern_id, "status": "DISCOVERED"} if pattern_id == "p-1" else None

    def list(self, **filters):
        return [{"pattern_id": "p-1", "status": filters.get("status") or "DISCOVERED"}]


def test_api_is_read_only_and_shadow_marked():
    api = PatternDiscoveryApiV1(_FakeService())
    found = api.get("p-1")
    missing = api.get("missing")
    discovered = api.discovered()

    assert found["status"] == 200
    assert missing["status"] == 404
    assert discovered["count"] == 1
    assert discovered["mode"] == "SHADOW_RESEARCH_ONLY"


def test_dashboard_read_models():
    record = {
        "pattern_id": "p-1",
        "title": "selected_plan = A",
        "status": "DISCOVERED",
        "direction": "POSITIVE",
        "discovery_method": "GROUP_COMPARISON",
        "sample_size": 20,
        "comparison_sample_size": 20,
        "support_rate": 90.0,
        "baseline_rate": 20.0,
        "uplift": 70.0,
        "average_r_multiple": 1.25,
        "expectancy_r": 1.25,
        "confidence_score": 88.0,
        "stability_score": 75.0,
        "definition": {
            "feature_conditions": {"selected_plan": "A"},
            "comparison_group": {"selected_plan": {"operator": "NOT_EQUALS", "value": "A"}},
        },
        "supporting_metrics": {"wins": 18},
        "warnings": ["Research candidate only."],
    }
    cards = build_pattern_cards(record)
    detail = build_pattern_detail_rows(record)
    workspace = build_pattern_workspace([record])

    assert cards["confidence_score"] == 88.0
    assert any(row["type"] == "FEATURE_CONDITION" for row in detail)
    assert workspace["cards"]["total_patterns"] == 1
    assert workspace["top_patterns"][0]["pattern_id"] == "p-1"
