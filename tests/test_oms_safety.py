import unittest
from src.decision.models import TradeDecision
from src.oms import ExecutionApprovalEngine, ExecutionMode
class OMSSafetyTests(unittest.TestCase):
 def test_auto_and_kill_switch_are_blocked(self):
  d=TradeDecision.new(snapshot_id="s",instrument="NIFTY",action="BUY",expiry=None,strike=None,option_type=None,entry=1,stop_loss=0,target_1=2,target_2=3,quantity=1,confidence=90,valid_until="x",status="RECOMMENDED",rule_version="1")
  e=ExecutionApprovalEngine(); self.assertFalse(e.evaluate(d,ExecutionMode.AUTO,kill_switch=False).approved); self.assertFalse(e.evaluate(d,ExecutionMode.ASSISTED,operator_approved=True,system_healthy=True,kill_switch=True).approved); self.assertTrue(e.evaluate(d,ExecutionMode.ASSISTED,operator_approved=True,system_healthy=True,kill_switch=False).approved)
