from src.analytics.engine import PerformanceAnalyticsEngine
from src.analytics.export import report_csv, report_json
from src.analytics.models import CompletedTrade


def trade(identifier, pnl, *, scenario="BREAKOUT", band="HIGH", strategy="1.0.0", minute=0):
    return CompletedTrade(
        trade_id=identifier, session_id="session-1", experiment_id=None, strategy_version=strategy,
        instrument="NIFTY", expiry="2026-07-23", direction="BUY", scenario=scenario,
        confidence_band=band, confidence_score=90.0, quantity=1, entry_price=100.0,
        exit_price=100.0 + pnl, opened_at=f"2026-07-19T09:{15 + minute:02d}:00+00:00",
        closed_at=f"2026-07-19T09:{16 + minute:02d}:00+00:00", realized_pnl=float(pnl),
        mae=-5.0, mfe=10.0,
    )


def test_profitability_and_win_rate_are_deterministic():
    engine = PerformanceAnalyticsEngine()
    report = engine.report([trade("b", -10, minute=1), trade("a", 20)])
    assert report.metrics["total_trades"] == 2
    assert report.metrics["win_rate"] == 0.5
    assert report.metrics["gross_profit"] == 20.0
    assert report.metrics["gross_loss"] == -10.0
    assert report.metrics["profit_factor"] == 2.0
    assert report.metrics["expectancy"] == 5.0
    assert report.metrics["maximum_drawdown"] == 10.0
    assert report.source_fingerprint == engine.report([trade("a", 20), trade("b", -10, minute=1)]).source_fingerprint


def test_equity_curve_and_scenario_aggregation():
    engine = PerformanceAnalyticsEngine()
    trades = [trade("a", 10, scenario="BREAKOUT"), trade("b", -5, scenario="REVERSAL", minute=1)]
    curve = engine.equity_curve(trades)
    report = engine.scenario_analysis(trades)
    assert [point["equity"] for point in curve] == [10.0, 5.0]
    assert curve[-1]["drawdown"] == 5.0
    assert report.groups["BREAKOUT"]["win_rate"] == 1.0
    assert report.groups["REVERSAL"]["win_rate"] == 0.0


def test_validation_and_strategy_comparisons():
    engine = PerformanceAnalyticsEngine()
    trades = [trade("a", 10, band="HIGH"), trade("b", -5, band="LOW", strategy="2.0.0", minute=1)]
    assert set(engine.validation_analysis(trades).groups) == {"HIGH", "LOW"}
    assert set(engine.strategy_comparison(trades).groups) == {"1.0.0", "2.0.0"}


def test_exports_are_stable_and_readable():
    report = PerformanceAnalyticsEngine().report([trade("a", 10)])
    assert report_json(report) == report_json(report)
    csv_value = report_csv(report)
    assert "metrics,total_trades,1" in csv_value
