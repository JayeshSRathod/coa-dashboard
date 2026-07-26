from types import SimpleNamespace

from src.application.fyers_worker import FyersUniversePollingWorker
from src.common.instruments import configured_index_requests
from src.market_intelligence.state import market_state, technical_confirmation


def test_configured_index_universe_defaults_and_rejects_unknown_names():
    assert [item.instrument_id for item in configured_index_requests()] == ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    assert [item.instrument_id for item in configured_index_requests("NIFTY,FINNIFTY")] == ["NIFTY", "FINNIFTY"]
    try:
        configured_index_requests("NIFTY,UNKNOWN")
    except ValueError as exc:
        assert "UNKNOWN" in str(exc)
    else:
        raise AssertionError("unknown instruments must be rejected")


def test_state_and_technical_confirmation_are_deterministic():
    spots = [100, 101, 102, 103, 104]
    assert market_state(spots)["state"].endswith("TRENDING_UP")
    technical = technical_confirmation(spots)
    assert technical["status"] == "PASS"
    assert technical["bias"] == "BULLISH"


def test_universe_worker_processes_every_request():
    class Factory:
        def status(self): return SimpleNamespace(ready=True, reason="ready")
        def provider(self): return SimpleNamespace(fetch_option_chain=lambda request: SimpleNamespace(captured_at=request.instrument_id))
    class Research:
        def __init__(self): self.values = []
        def process(self, snapshot): self.values.append(snapshot); return snapshot.captured_at
    research = Research()
    cycle = FyersUniversePollingWorker(Factory(), research, configured_index_requests("NIFTY,FINNIFTY"), market_open=lambda: True).run_once()
    assert len(cycle.cycles) == 2
    assert cycle.failures == 0
    assert [item.captured_at for item in research.values] == ["NIFTY", "FINNIFTY"]
