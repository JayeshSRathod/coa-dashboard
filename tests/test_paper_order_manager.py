import unittest
from src.decision.models import TradeDecision
from src.paper_trading import PaperOrderManager
class PaperOrderManagerTests(unittest.TestCase):
 def test_only_approved_trade_actions_create_validated_paper_orders(self):
  d=TradeDecision.new(snapshot_id="s",instrument="NIFTY",action="BUY",expiry=None,strike=None,option_type=None,entry=100,stop_loss=90,target_1=110,target_2=120,quantity=1,confidence=90,valid_until="x",status="RECOMMENDED",rule_version="1",metadata={"execution_mode":"DISABLED"}); self.assertEqual(PaperOrderManager().create(d).status,"VALIDATED")
