from __future__ import annotations

import unittest

from src.market_data.mappers.fyers_mapper import map_fyers_option_chain


class FyersCaptureMetadataTests(unittest.TestCase):
    def test_provider_expiry_and_quote_quantities_are_preserved(self) -> None:
        snapshot = map_fyers_option_chain(
            {"spot_price": 24_000, "expiryDate": "2026-08-06", "optionsChain": [
                {"option_type": "CE", "strike_price": 24_000, "ltp": 100,
                 "volume": 10, "oi": 20, "bid": 99, "ask": 101,
                 "bid_qty": 250, "ask_qty": 175},
            ]},
            instrument_id="NIFTY", expiry="", captured_at="2026-08-01T09:15:00+05:30",
            provider_symbol="NSE:NIFTY50-INDEX", capture_profile="research_core_v1",
        )
        self.assertEqual("2026-08-06", snapshot.expiry)
        self.assertEqual(250, snapshot.contracts[0].bid_quantity)
        self.assertEqual(175, snapshot.contracts[0].ask_quantity)
        self.assertEqual("NSE:NIFTY50-INDEX", snapshot.metadata["provider_symbol"])
        row = snapshot.coa_rows()[0]
        self.assertEqual(250, row["Call_Bid_Qty"])


if __name__ == "__main__":
    unittest.main()
