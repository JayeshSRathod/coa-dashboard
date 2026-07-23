from unittest import TestCase

from src.configuration_console.secrets import InMemorySecretStore
from src.execution.config import PaperExecutionConfig
from src.execution.engine import PaperExecutionEngine
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FYERS_SECRETS, FyersDataSessionFactory
from src.paper_runtime import PaperRuntimeService
from src.signal.models import ResearchSignal


def _signal() -> ResearchSignal:
    return ResearchSignal.new(signal_id="SIG-1", snapshot_id="S-1", coa_result_id="COA-1", validation_id="VAL-1", session_id="SESSION-1", experiment_id=None, strategy_version="1", signal_version="1", instrument="NIFTY", expiry="2026-07-30", signal_type="BUY", signal_state="ACTIVE", direction="BUY", entry_price=100.0, stop_loss=90.0, target_1=110.0, target_2=120.0, trailing_reference=None, confidence_score=80, confidence_band="HIGH", scenario="S1", eos=None, eor=None, momentum=None, diversion=None)


class FyersPaperRuntimeTests(TestCase):
    def test_fyers_factory_requires_daily_secret_store_session_and_normalizes_data(self):
        secrets = InMemorySecretStore()
        factory = FyersDataSessionFactory(secrets)
        self.assertFalse(factory.status().ready)
        for key, value in {"app_id": "APP-200", "secret_key": "secret", "redirect_uri": "https://local/callback", "access_token": "daily-token"}.items():
            secrets.set(FYERS_SECRETS[key], value)
        provider = factory.provider(fetcher=lambda *_: {"optionsChain": [{"ltp": 25000}, {"option_type": "CE", "strike_price": 25000, "ltp": 100, "oi": 10, "volume": 20}, {"option_type": "PE", "strike_price": 25000, "ltp": 90, "oi": 12, "volume": 18}]})
        snapshot = provider.fetch_option_chain(OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", "2026-07-30"))
        self.assertEqual(snapshot.provider, "FYERS")
        self.assertEqual(snapshot.spot, 25000)

    def test_runtime_is_paper_only_and_emits_simulated_events(self):
        runtime = PaperRuntimeService(PaperExecutionEngine(PaperExecutionConfig(entry_price_source="LTP", exit_price_source="LTP")))
        with self.assertRaises(ValueError):
            runtime.start("LIVE")
        runtime.start("PAPER")
        first = {"snapshot_id": "S-1", "market_captured_at": "2026-07-23T09:15:00Z", "spot": 100.0, "atm_strike": 100.0, "option_chain": [{"Strike": 100.0, "Call_LTP": 100.0, "Put_LTP": 90.0}]}
        trade = runtime.submit_signal(_signal(), first)
        self.assertIsNotNone(trade)
        events = runtime.process_snapshot({**first, "snapshot_id": "S-2", "market_captured_at": "2026-07-23T09:16:00Z"})
        self.assertTrue(any(item.event_type == "ENTRY_FILLED" for item in events))
        self.assertEqual(runtime.status().mode, "PAPER")
