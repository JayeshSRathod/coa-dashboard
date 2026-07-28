import unittest

from dashboard.option_ladder import build_option_ladder, filter_ladder_around_atm


class OptionLadderTests(unittest.TestCase):
    def test_builds_ce_left_strike_centre_pe_right_rows_and_atm(self):
        rows = build_option_ladder([
            {"Strike": 23950, "Call_OI": 10, "Call_LTP": 20, "Put_OI": 15, "Put_LTP": 25},
            {"Strike": 24000, "Call_OI": 20, "Call_Bid": 10, "Call_Ask": 11, "Call_OI_Change": 5, "Call_Delta": 0.5, "Put_OI": 25, "Put_Bid": 12, "Put_Ask": 13, "Put_OI_Change": 7},
        ], 23980)
        self.assertEqual(rows[1]["ce_spread"], 1.0)
        self.assertEqual(rows[1]["pe_spread"], 1.0)
        self.assertTrue(rows[1]["is_atm"])
        self.assertEqual(filter_ladder_around_atm(rows, 1), rows)
