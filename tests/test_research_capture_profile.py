from __future__ import annotations

import unittest
from datetime import datetime

from src.research.capture_profile import capture_metadata


class CaptureProfileTests(unittest.TestCase):
    def test_records_provider_identity_and_full_returned_window(self) -> None:
        metadata = capture_metadata(
            profile="research_core_v1", provider_symbol="NSE:NIFTY50-INDEX",
            requested_expiry="", resolved_expiry="2026-08-06", spot=24_000,
            atm_strike=24_000, strikes=[23_900, 23_950, 24_000, 24_050], strike_count=10,
        )
        self.assertEqual("NSE:NIFTY50-INDEX", metadata["provider_symbol"])
        self.assertEqual(4, metadata["strike_window"]["returned_strike_count"])
        self.assertEqual("provider_returned_chain; no CQRP strike filtering", metadata["strike_window"]["selection"])

    def test_unknown_expiry_is_not_invented(self) -> None:
        metadata = capture_metadata(
            profile="research_core_v1", provider_symbol="NSE:FINNIFTY-INDEX",
            requested_expiry=None, resolved_expiry=None, spot=0, atm_strike=None,
            strikes=[], strike_count=10,
        )
        self.assertIsNone(metadata["days_to_expiry"])


if __name__ == "__main__":
    unittest.main()
