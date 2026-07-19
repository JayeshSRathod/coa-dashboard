import unittest
from src.trade_journal.analytics import classify_trade,violations,statistics
from src.trade_journal.service import TradeJournalService
from src.persistence.connection import connect
from src.persistence.migration import apply_migrations
from src.persistence.schema import RESEARCH_MIGRATIONS
from src.persistence.trade_journal_repository import TradeJournalRepository,LearningRepository,PerformanceRepository,ComplianceRepository,TimelineRepository,StatisticsRepository,ReportRepository
class TradeJournalTests(unittest.TestCase):
 def setUp(self):
  c=connect(":memory:");apply_migrations(c,RESEARCH_MIGRATIONS)
  self.s=TradeJournalService({"journal":TradeJournalRepository(c),"learning":LearningRepository(c),"performance":PerformanceRepository(c),"compliance":ComplianceRepository(c),"timeline":TimelineRepository(c),"statistics":StatisticsRepository(c),"report":ReportRepository(c)})
  self.t={"trade_id":"t1","pnl":10,"quantity":1,"strategy":"COA","instrument":"NIFTY","market":"NSE","sector":"Index","confidence":80,"validation_complete":True,"direction":"LONG","entry_price":100,"exit_price":110,"stop_loss":95}
 def test_journal_classification_compliance_learning_reports(self):
  _,e=self.s.create_trade_journal(self.t,{"max_quantity":2});self.assertIn("WINNING_TRADE",e["categories"]);self.assertEqual(e["compliance_score"],100)
  self.assertEqual(self.s.calculate_trade_statistics()["net_pnl"],10);self.assertIn("COA",self.s.update_learning_repository()["strategy"]);self.assertEqual(self.s.generate_report("DAILY")["trades"],1)
 def test_rule_violations_and_statistics(self):
  bad=dict(self.t,trade_id="t2",quantity=3,exit_price=90,validation_complete=False,pnl=-5)
  self.assertEqual(len(violations(bad,{"max_quantity":2})),3);self.s.create_trade_journal(bad,{"max_quantity":2});self.assertEqual(len(self.s.find_rule_violations()),1)
if __name__=="__main__":unittest.main()
