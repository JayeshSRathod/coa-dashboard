from __future__ import annotations

from src.premarket_validation.engine import PreMarketValidationEngine
from src.premarket_validation.models import PreMarketObservation
from src.trade_planning.models import OpeningPlan, TradePlan


def _plan(**overrides):
    values = {
        "snapshot_id": "snap-close",
        "signal_id": "sig-1",
        "risk_decision_id": "risk-1",
        "instrument": "NIFTY",
        "expiry": "2026-08-06",
        "planning_horizon": "NEXT_SESSION",
        "market_bias": "BULLISH",
        "expected_opening": "GAP_UP",
        "direction": "BUY",
        "option_type": "CE",
        "entry": 25100.0,
        "stop_loss": 24980.0,
        "target_1": 25250.0,
        "target_2": 25400.0,
        "confidence_score": 82.0,
        "readiness": "READY",
        "status": "PRELIMINARY",
        "valid_for_session": None,
        "rationale": ("Bullish closing structure",),
        "warnings": (),
        "opening_plans": (
            OpeningPlan("A", "Expected", "PAPER_BUY_CE", "Confirm", "Cancel"),
            OpeningPlan("B", "Flat", "PAPER_BUY_CE", "Confirm", "Cancel"),
            OpeningPlan("C", "Adverse", "WAIT_OR_CANCEL", "Wait", "Cancel"),
        ),
        "evidence": {},
        "planner_version": "trade-planner-v1",
    }
    values.update(overrides)
    return TradePlan.new(**values)


def _observation(plan: TradePlan, **overrides):
    values = {
        "trade_plan_id": plan.trade_plan_id,
        "snapshot_id": "snap-open",
        "observed_at": "2026-08-04T03:35:00+00:00",
        "instrument": plan.instrument,
        "planning_horizon": plan.planning_horizon,
        "previous_close": 25000.0,
        "observed_spot": 25075.0,
        "coa_bias": "BULLISH",
        "technical_status": "CONFIRMED",
        "technical_bias": "BULLISH",
        "momentum_state": "STRONG",
        "risk_status": "PASS",
        "data_quality": "PASS",
    }
    values.update(overrides)
    return PreMarketObservation(**values)


def test_expected_gap_with_aligned_structure_is_validated_plan_a():
    plan = _plan()
    result = PreMarketValidationEngine().validate(plan, _observation(plan))
    assert result.validation_result == "VALIDATED"
    assert result.selected_plan == "A"
    assert result.opening_classification == "GAP_UP"
    assert result.confidence_after > result.confidence_before


def test_flat_opening_is_modified_plan_b():
    plan = _plan()
    observation = _observation(plan, observed_spot=25020.0)
    result = PreMarketValidationEngine().validate(plan, observation)
    assert result.opening_classification == "FLAT"
    assert result.validation_result == "MODIFIED"
    assert result.selected_plan == "B"


def test_adverse_gap_cancels_plan_c():
    plan = _plan()
    observation = _observation(
        plan,
        observed_spot=24800.0,
        coa_bias="BEARISH",
        technical_bias="BEARISH",
    )
    result = PreMarketValidationEngine().validate(plan, observation)
    assert result.validation_result == "CANCELLED"
    assert result.selected_plan == "C"
    assert result.confidence_after <= 25.0


def test_data_quality_failure_is_hard_cancel():
    plan = _plan()
    result = PreMarketValidationEngine().validate(
        plan,
        _observation(plan, data_quality="FAILED"),
    )
    assert result.validation_result == "CANCELLED"
    assert result.confidence_after == 0.0
    assert any("data quality" in reason.lower() for reason in result.reasons)


def test_high_news_risk_is_hard_cancel():
    plan = _plan()
    result = PreMarketValidationEngine().validate(
        plan,
        _observation(plan, news_risk="HIGH"),
    )
    assert result.validation_result == "CANCELLED"
    assert result.selected_plan == "C"


def test_intraday_horizon_uses_same_engine():
    plan = _plan(planning_horizon="INTRADAY")
    observation = _observation(
        plan,
        planning_horizon="INTRADAY",
        observed_at="2026-08-03T06:00:00+00:00",
    )
    result = PreMarketValidationEngine().validate(plan, observation)
    assert result.planning_horizon == "INTRADAY"
    assert any("intraday" in reason.lower() for reason in result.reasons)


def test_identity_mismatch_is_rejected():
    plan = _plan()
    observation = _observation(plan, instrument="BANKNIFTY")
    try:
        PreMarketValidationEngine().validate(plan, observation)
    except ValueError as exc:
        assert "instrument" in str(exc)
    else:
        raise AssertionError("expected identity mismatch")
