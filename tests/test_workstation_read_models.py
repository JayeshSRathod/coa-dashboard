"""Tests for deterministic, presentation-only cockpit read models."""

from dashboard.workstation.read_models import conditional_plan, index_comparison, option_activity_rows, scenario_evidence
from dashboard.workstation.render import render_option_activity


def test_option_activity_preserves_per_strike_evidence() -> None:
    rows = option_activity_rows([{"strike": 25000, "is_atm": True, "ce_oi": 10, "pe_oi": 12, "ce_volume": 4, "pe_volume": 5, "ce_oi_change": 2, "pe_oi_change": -1}])
    assert rows == [{"strike": 25000.0, "is_atm": True, "ce_oi": 10.0, "pe_oi": 12.0, "ce_volume": 4.0, "pe_volume": 5.0, "ce_oi_change": 2.0, "pe_oi_change": -1.0}]


def test_comparison_ranks_existing_scores_without_inventing_values() -> None:
    ranked = index_comparison([{"instrument": "FINNIFTY", "confidence": 20}, {"instrument": "NIFTY", "confidence": 80}])
    assert [row["instrument"] for row in ranked] == ["NIFTY", "FINNIFTY"]
    assert [row["rank"] for row in ranked] == [1, 2]


def test_plan_and_scenario_are_explicitly_conditional_and_building() -> None:
    assert conditional_plan(None)["state"] == "NO_PLAN"
    assert scenario_evidence({"structural_scenario_number": 7, "tactical_scenario_number": 15})["status"] == "BUILDING"


def test_option_activity_renders_a_chart_without_trade_decision() -> None:
    class StreamlitStub:
        def markdown(self, *_args, **_kwargs): pass
        def plotly_chart(self, figure, **_kwargs): self.figure = figure
        def caption(self, *_args, **_kwargs): pass
    st = StreamlitStub()
    render_option_activity(st, option_activity_rows([{"strike": 25000, "is_atm": True, "ce_oi": 10, "pe_oi": 12}]))
    assert {trace.name for trace in st.figure.data} == {"CE OI", "PE OI", "Volume", "OI change"}
