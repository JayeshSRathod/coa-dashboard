import unittest
from dashboard.services import DashboardApplicationService
from dashboard.exports import export_csv,export_json
from dashboard.view_models import mask_secret
class DashboardTests(unittest.TestCase):
 def test_views_exports_masks_and_errors(self):
  s=DashboardApplicationService({"home":lambda:{"cards":{"mode":"PAPER"},"rows":[{"symbol":"NIFTY"}]},"market":lambda:1/0})
  self.assertEqual(s.get_home_dashboard().cards["mode"],"PAPER");self.assertEqual(s.get_market_dashboard().freshness.status,"UNAVAILABLE")
  self.assertIn("symbol",export_csv([{"symbol":"NIFTY"}]));self.assertIn("NIFTY",export_json([{"symbol":"NIFTY"}]));self.assertEqual(mask_secret("x"),"********")
if __name__=="__main__":unittest.main()
