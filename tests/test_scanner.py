import unittest
from src.scanner import OpportunityScanner
class ScannerTests(unittest.TestCase):
 def test_filters_and_ranks_candidates_without_orders(self):
  rows=[{"instrument_id":"B","price":100,"tradable":True,"liquidity":80,"quality":80,"coa":80,"trend_score":80,"momentum":70,"volume":70,"relative_strength":70,"risk":80,"volatility":70},{"instrument_id":"A","price":100,"tradable":True,"liquidity":80,"quality":80,"coa":90,"trend_score":90,"momentum":80,"volume":80,"relative_strength":80,"risk":80,"volatility":80},{"instrument_id":"X","price":100,"tradable":False,"liquidity":100,"quality":100}]
  result=OpportunityScanner().rank(rows); self.assertEqual([x.instrument_id for x in result],["A","B"]); self.assertEqual(result[0].entry_zone,100)
