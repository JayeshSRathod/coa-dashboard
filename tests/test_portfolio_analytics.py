import unittest
from src.portfolio_analytics.greeks import calculate_greeks
from src.portfolio_analytics.options import analyze_option_chain, classify_oi_change, iv_statistics, max_pain
from src.portfolio_analytics.engine import calculate_portfolio
from src.portfolio_analytics.strategy import analyze_strategy
from src.portfolio_analytics.stress import stress_test
from src.persistence.connection import connect
from src.persistence.migration import apply_migrations
from src.persistence.schema import RESEARCH_MIGRATIONS
from src.persistence.portfolio_analytics_repository import PortfolioAnalyticsRepository


class PortfolioAnalyticsTests(unittest.TestCase):
 def test_greeks_are_deterministic(self):
  first=calculate_greeks(spot=100,strike=100,time_years=.5,volatility=.2,risk_free_rate=.05,option_type="CALL")
  self.assertEqual(first,calculate_greeks(spot=100,strike=100,time_years=.5,volatility=.2,risk_free_rate=.05,option_type="CALL"))
  self.assertGreater(first.delta,0)
 def test_chain_iv_and_max_pain(self):
  chain=[{"strike":90,"option_type":"CALL","oi":10,"bid":1,"ask":2},{"strike":100,"option_type":"CALL","oi":20,"bid":1,"ask":2},{"strike":90,"option_type":"PUT","oi":30,"bid":1,"ask":2},{"strike":100,"option_type":"PUT","oi":10,"bid":1,"ask":2}]
  self.assertEqual(analyze_option_chain(chain,95)["pcr"],40/30)
  self.assertEqual(classify_oi_change(price_change=-1,oi_change=-1),"LONG_UNWINDING")
  self.assertEqual(iv_statistics(20,[10,20,30])["iv_percentile"],2/3*100)
  self.assertIn(max_pain(chain)["max_pain"],[90.0,100.0])
 def test_portfolio_payoff_stress_and_repository(self):
  pos={"position_id":"p1","symbol":"NIFTY","quantity":1,"average_price":100}
  self.assertEqual(calculate_portfolio([pos],{"p1":110})["pnl"],10)
  payoff=analyze_strategy(legs=[{"option_type":"CALL","side":"LONG","strike":100,"premium":5,"quantity":1}],underlying_prices=[90,100,110])
  self.assertEqual(payoff["maximum_profit"],5)
  self.assertEqual(stress_test([pos],{"p1":100},[{"underlying_change_pct":10}])[0]["pnl"],10)
  c=connect(":memory:"); apply_migrations(c,RESEARCH_MIGRATIONS); repo=PortfolioAnalyticsRepository(c)
  a=repo.append(subject_id="x",payload={"pnl":10},fingerprint="same"); b=repo.append(subject_id="x",payload={"pnl":10},fingerprint="same")
  self.assertEqual(a,b)
if __name__=="__main__": unittest.main()
