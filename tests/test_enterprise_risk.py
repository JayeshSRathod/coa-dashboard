import unittest
from src.enterprise_risk import EnterpriseRiskEngine
class RiskTests(unittest.TestCase):
 def test_deterministic_allow_resize_block(self):
  e=EnterpriseRiskEngine(); self.assertEqual(e.assess(requested_quantity=1,unit_risk=100,capital=1000,used_capital=0).status,"ALLOW"); self.assertEqual(e.assess(requested_quantity=10,unit_risk=100,capital=1000,used_capital=500).status,"RESIZE"); self.assertEqual(e.assess(requested_quantity=1,unit_risk=100,capital=1000,used_capital=800).status,"BLOCK")
