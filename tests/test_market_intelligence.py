import unittest
from src.market_intelligence.scanners import ScannerRegistry,ThresholdScanner
from src.market_intelligence.analytics import calculate_rank,market_breadth,sector_strength,detect_themes,generate_watchlists,alerts_for
class MarketIntelligenceTests(unittest.TestCase):
 def setUp(self):
  self.records=[{"symbol":"BANK","sector":"Banking","trend":90,"relative_strength":80,"delivery_spike":3,"oi_change":25,"change_pct":2},{"symbol":"IT","sector":"IT","trend":40,"relative_strength":20,"change_pct":-1}]
 def test_scanner_ranking_and_watchlists(self):
  reg=ScannerRegistry();reg.register(ThresholdScanner("TREND","trend",50,"SWING")); results=reg.run(self.records)
  self.assertEqual([r.symbol for r in results],["BANK"]);self.assertEqual(calculate_rank({"trend":100}),25);self.assertEqual(len(generate_watchlists(results)["DAILY"]),1)
 def test_breadth_sector_themes_and_alerts(self):
  self.assertEqual(market_breadth(self.records)["advances"],1);self.assertEqual(sector_strength(self.records)[0]["sector"],"Banking")
  self.assertEqual(len(detect_themes(self.records)),3);self.assertEqual(alerts_for([],[]),[])
if __name__=="__main__":unittest.main()
