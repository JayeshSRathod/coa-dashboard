from __future__ import annotations

from src.trade_planning.engine import TradePlanningEngine
from src.trade_planning.models import TradePlanningInput


def _input(**overrides):
    values = {
        "snapshot_id": "snap-1",
        "signal_id": "sig-1",
        "risk_decision_id": "risk-1",
        "instrument": "NIFTY",
        "expiry": "2026-08-06",
        "spot": 25080.0,
        "scenario_number": 7,
        "scenario": "Powerful bull run",
        "risk_mode": "NORMAL",
        "support": 24950.0,
        "resistance": 25000.0,
        "eos": 24920.0,
        "eor": 25020.0,
        "direction": "BUY",
        "signal_type": "BUY",
        "entry": 25100.0,
        "stop_loss": 24980.0,
        "target_1": 25250.0,
        "target_2": 25400.0,
        "confidence_score": 82.0,
        "validation_passed": True,
        "technical_status": "CONFIRMED",
        "technical_bias": "BULLISH",
        "momentum_state": "STRONG",
        "evidence": {"source": "test"},
    }
    values.update(overrides)
    return TradePlanningInput(**values)


def test_bullish_close_above_eor_generates_ready_gap_up_ce_plan():
    plan = TradePlanningEngine().plan(_input())

    assert plan.market_bias == "BULLISH"
    assert plan.expected_opening == "GAP_UP"
    assert plan.readiness == "READY"
    assert plan.direction == "BUY"
    assert plan.option_type == "CE"
    assert plan.entry == 25100.0
    assert plan.confidence_score == 95.0
    assert [item.code for item in plan.opening_plans] == ["A", "B", "C"]
    assert plan.opening_plans[0].action == "PAPER_BUY_CE"
    assert plan.status == "PRELIMINARY"


def test_bearish_close_below_eos_generates_ready_gap_down_pe_plan():
    plan = TradePlanningEngine().plan(
        _input(
            spot=24780.0,
            scenario_number=6,
            scenario="Severe bearish state",
            support=24850.0,
            resistance=25000.0,
            eos=24820.0,
            eor=25050.0,
            direction="SELL",
            signal_type="SELL",
            technical_bias="BEARISH",
        )
    )

    assert plan.market_bias == "BEARISH"
    assert plan.expected_opening == "GAP_DOWN"
    assert plan.readiness == "READY"
    assert plan.option_type == "PE"
    assert plan.opening_plans[0].action == "PAPER_BUY_PE"


def test_halt_scenario_is_blocked_and_has_no_trade_levels():
    plan = TradePlanningEngine().plan(
        _input(scenario_number=8, risk_mode="HALT_TRADING")
    )

    assert plan.market_bias == "UNCERTAIN"
    assert plan.expected_opening == "UNCERTAIN"
    assert plan.readiness == "BLOCKED"
    assert plan.direction is None
    assert plan.option_type is None
    assert plan.entry is None
    assert plan.confidence_score == 0.0
    assert all(item.action in {"WAIT", "CANCEL"} for item in plan.opening_plans)


def test_failed_validation_is_observe_only():
    plan = TradePlanningEngine().plan(_input(validation_passed=False))

    assert plan.readiness == "OBSERVE_ONLY"
    assert plan.direction is None
    assert plan.confidence_score <= 49.0
    assert any("Validation did not pass" in warning for warning in plan.warnings)


def test_low_confidence_valid_plan_is_conditional():
    plan = TradePlanningEngine().plan(_input(confidence_score=55.0))

    assert plan.readiness == "CONDITIONAL"
    assert plan.direction == "BUY"
    assert plan.option_type == "CE"
    assert any("below the ready-plan threshold" in warning for warning in plan.warnings)


def test_planner_does_not_mutate_input_evidence():
    evidence = {"nested": "value"}
    source = _input(evidence=evidence)
    plan = TradePlanningEngine().plan(source)

    evidence["nested"] = "changed"
    assert source.evidence["nested"] == "value"
    assert plan.evidence["nested"] == "value"
