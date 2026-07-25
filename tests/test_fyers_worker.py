import unittest
from types import SimpleNamespace

from datetime import datetime, timezone

from src.application.fyers_worker import FyersPollingWorker, market_is_open
from src.market_data.contracts import OptionChainRequest


class FyersPollingWorkerTests(unittest.TestCase):
    def test_market_session_uses_india_weekday_hours(self):
        self.assertTrue(market_is_open(datetime(2026, 7, 27, 4, 0, tzinfo=timezone.utc)))
        self.assertFalse(market_is_open(datetime(2026, 7, 25, 4, 0, tzinfo=timezone.utc)))
        self.assertFalse(market_is_open(datetime(2026, 7, 27, 3, 0, tzinfo=timezone.utc)))

    def test_worker_processes_one_ready_snapshot(self):
        snapshot = SimpleNamespace(captured_at="2026-07-25T09:30:00+00:00")

        class Factory:
            def status(self):
                return type("Status", (), {"ready": True, "reason": "ready"})()

            def provider(self):
                return type("Provider", (), {"fetch_option_chain": lambda _, __: snapshot})()

        class Research:
            def process(self, value):
                self.value = value
                return "processed"

        research = Research()
        cycle = FyersPollingWorker(Factory(), research, OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", ""), market_open=lambda: True).run_once()

        self.assertEqual(cycle.outcome, "processed")
        self.assertIsNone(cycle.error)
        self.assertIs(research.value, snapshot)

    def test_worker_reports_missing_daily_session_without_fetching(self):
        class Factory:
            def status(self):
                return type("Status", (), {"ready": False, "reason": "daily token missing"})()

        cycle = FyersPollingWorker(Factory(), object(), OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", ""), market_open=lambda: True).run_once()

        self.assertEqual(cycle.error, "daily token missing")


if __name__ == "__main__":
    unittest.main()
