from src.risk.config import RiskConfig
from src.risk.engine import PortfolioRiskEngine
from src.risk.models import Portfolio
from src.signal.models import ResearchSignal


def signal(**overrides):
    values = {
        "signal_id": "signal-1", "snapshot_id": "snapshot-1", "coa_result_id": "coa-1",
        "validation_id": "validation-1", "session_id": "session-1", "experiment_id": None,
        "strategy_version": "1.0.0", "signal_version": "1.0.0", "instrument": "NIFTY",
        "expiry": "2026-07-23", "signal_type": "BUY", "signal_state": "ACTIVE",
        "direction": "BULLISH", "entry_price": 100.0, "stop_loss": 90.0,
        "target_1": None, "target_2": None, "trailing_reference": None,
        "confidence_score": 90.0, "confidence_band": "HIGH", "scenario": "S1",
        "eos": None, "eor": None, "momentum": None, "diversion": None,
        "reasons": [], "warnings": [], "details": {}, "processing_time_ms": 0.0,
        "created_at": "2026-07-19T09:15:00+00:00", "created_by": "test",
    }
    values.update(overrides)
    return ResearchSignal.new(**values)


def portfolio():
    return Portfolio.new(portfolio_id="portfolio-1", name="Research", owner="tester", initial_capital=1000.0)


def test_fixed_quantity_is_approved_deterministically():
    engine = PortfolioRiskEngine(RiskConfig(fixed_quantity=2, cash_reserve_percent=0.0))
    first = engine.evaluate(signal(), portfolio())
    second = engine.evaluate(signal(), portfolio())
    assert first.decision == "APPROVED"
    assert first.approved_quantity == 2
    assert first.requested_quantity == second.requested_quantity
    assert first.capital_required == second.capital_required


def test_limited_capital_reduces_size():
    engine = PortfolioRiskEngine(RiskConfig(fixed_quantity=10, cash_reserve_percent=0.0))
    decision = engine.evaluate(signal(), portfolio(), invested=750.0)
    assert decision.decision == "REDUCED_SIZE"
    assert decision.approved_quantity == 2
    assert decision.capital_required == 200.0


def test_daily_loss_blocks_candidate():
    engine = PortfolioRiskEngine(RiskConfig(cash_reserve_percent=0.0, max_daily_loss=100.0))
    decision = engine.evaluate(signal(), portfolio(), daily_pnl=-100.0)
    assert decision.decision == "REJECTED"
    assert "daily loss limit breached" in decision.rejection_reason


def test_fixed_risk_requires_stop_loss():
    engine = PortfolioRiskEngine(RiskConfig(sizing_method="FIXED_RISK", fixed_risk=100.0))
    decision = engine.evaluate(signal(stop_loss=None), portfolio())
    assert decision.decision == "REJECTED"
    assert decision.approved_quantity == 0


def test_exposure_limit_blocks_candidate():
    engine = PortfolioRiskEngine(RiskConfig(cash_reserve_percent=0.0, max_instrument_exposure=150.0))
    decision = engine.evaluate(signal(), portfolio(), instrument_exposure=100.0)
    assert decision.decision == "REJECTED"
    assert "instrument exposure limit breached" in decision.rejection_reason
