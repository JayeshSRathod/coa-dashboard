from __future__ import annotations

import unittest

from src.research.market_data_audit import MarketDataAvailabilityAuditor


class MarketDataAvailabilityAuditorTests(unittest.TestCase):
    def test_reports_coverage_by_instrument_and_expiry(self) -> None:
        snapshots = [
            {
                "instrument": "NIFTY",
                "expiry": "2026-07-30",
                "data_quality_status": "VALID",
                "option_chain": [
                    {
                        "Call_Bid": 12.0, "Put_Bid": 9.0,
                        "Call_Ask": 12.5, "Put_Ask": 9.5,
                        "Call_OI_Change": 0.0, "Put_OI_Change": 4.0,
                        "Call_IV": 11.2, "Put_IV": 12.1,
                        "Call_Delta": 0.5, "Put_Delta": -0.5,
                        "Call_Gamma": 0.1, "Put_Gamma": 0.1,
                        "Call_Theta": -0.2, "Put_Theta": -0.2,
                        "Call_Vega": 0.3, "Put_Vega": 0.3,
                    }
                ],
            }
        ]

        report = MarketDataAvailabilityAuditor().audit(snapshots)[0]

        self.assertEqual(report.instrument, "NIFTY")
        self.assertEqual(report.expiry, "2026-07-30")
        self.assertTrue(report.provider_fields_ready_for_shadow_study)
        coverage = {item.field: item.coverage_percent for item in report.field_coverage}
        self.assertEqual(coverage["bid"], 100.0)
        self.assertEqual(coverage["oi_change"], 100.0)

    def test_missing_or_invalid_quotes_do_not_pass_the_gate(self) -> None:
        snapshots = [
            {
                "instrument": "NIFTY",
                "expiry": "2026-07-30",
                "data_quality_status": "DEGRADED",
                "option_chain": [{"Call_Bid": None, "Put_Bid": 0.0, "Call_Ask": None, "Put_Ask": 0.0}],
            }
        ]

        report = MarketDataAvailabilityAuditor().audit(snapshots)[0]

        self.assertFalse(report.provider_fields_ready_for_shadow_study)
        coverage = {item.field: item.coverage_percent for item in report.field_coverage}
        self.assertEqual(coverage["bid"], 0.0)
        self.assertEqual(coverage["ask"], 0.0)


if __name__ == "__main__":
    unittest.main()
