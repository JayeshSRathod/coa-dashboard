import tempfile
import unittest
from pathlib import Path

from src.application.fyers_research import FyersResearchService
from src.market_data.models import OptionChainSnapshot, OptionContract


class FyersResearchServiceTests(unittest.TestCase):
    def test_live_snapshot_is_appended_then_processed_by_coa_and_validation(self):
        database = Path(tempfile.mkdtemp()) / "research.db"
        service = FyersResearchService(database)
        captured_at = "2026-07-25T09:30:00+00:00"
        contracts = tuple(
            OptionContract("NIFTY", strike, "", option_type, premium, "FYERS", captured_at, volume=volume, oi=oi)
            for strike, option_type, premium, volume, oi in (
                (23700, "CE", 120, 100, 300), (23700, "PE", 40, 220, 500),
                (23750, "CE", 85, 150, 400), (23750, "PE", 65, 180, 450),
                (23800, "CE", 55, 240, 600), (23800, "PE", 100, 90, 250),
            )
        )
        snapshot = OptionChainSnapshot.new(instrument_id="NIFTY", spot=23767.0, expiry="", provider="FYERS", captured_at=captured_at, contracts=contracts)

        outcome = service.process(snapshot)

        self.assertIsNone(outcome.error)
        self.assertIsNotNone(outcome.snapshot_id)
        self.assertIsNotNone(outcome.coa_result)
        self.assertIsNotNone(outcome.validation_result)
        self.assertEqual(service.latest("NIFTY").snapshot_id, outcome.snapshot_id)


if __name__ == "__main__":
    unittest.main()
