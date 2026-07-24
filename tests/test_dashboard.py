import unittest
from unittest.mock import Mock, patch

from dashboard.exports import export_csv, export_json
from dashboard.services import DashboardApplicationService
from dashboard.view_models import mask_secret
from src.configuration_console.secrets import InMemorySecretStore
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FYERS_SECRETS, FyersDataSessionFactory
from src.market_data.providers.fyers_provider import FyersProvider


class DashboardTests(unittest.TestCase):
    def test_views_exports_masks_and_errors(self):
        service = DashboardApplicationService({
            "home": lambda: {"cards": {"mode": "PAPER"}, "rows": [{"symbol": "NIFTY"}]},
            "market": lambda: 1 / 0,
        })

        self.assertEqual(service.get_home_dashboard().cards["mode"], "PAPER")
        self.assertEqual(service.get_market_dashboard().freshness.status, "UNAVAILABLE")
        self.assertIn("symbol", export_csv([{"symbol": "NIFTY"}]))
        self.assertIn("NIFTY", export_json([{"symbol": "NIFTY"}]))
        self.assertEqual(mask_secret("x"), "********")

    def test_live_fyers_market_requires_a_daily_session_without_exposing_secrets(self):
        unavailable = DashboardApplicationService(secret_store=InMemorySecretStore())
        view = unavailable.get_live_fyers_market(OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", ""))
        self.assertEqual(view.freshness.status, "NOT_CONFIGURED")

        secrets = InMemorySecretStore({key: "configured" for key in FYERS_SECRETS.values()})

        class TestFactory(FyersDataSessionFactory):
            def provider(self):
                return super().provider(fetcher=lambda *_: {
                    "optionsChain": [
                        {"ltp": 25000},
                        {"option_type": "CE", "strike_price": 25000, "ltp": 100, "oi": 10, "volume": 20},
                    ]
                })

        view = DashboardApplicationService(fyers_factory=TestFactory(secrets)).get_live_fyers_market(
            OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", "", 5)
        )
        self.assertEqual(view.freshness.source, "FYERS")
        self.assertEqual(view.cards["spot"], 25000)
        self.assertEqual(view.cards["mode"], "DATA_ONLY_PAPER")

    @patch("src.market_data.providers.fyers_provider.requests.put")
    def test_fyers_transport_uses_bearer_daily_token(self, put):
        response = Mock(status_code=200)
        response.json.return_value = {"s": "ok", "data": {"optionsChain": []}}
        put.return_value = response

        raw = FyersProvider._fetch_raw("APP-200", "daily-token", "NSE:NIFTY50-INDEX", 5)

        self.assertEqual(raw, {"optionsChain": []})
        self.assertEqual(put.call_args.kwargs["headers"]["Authorization"], "Bearer daily-token")


if __name__ == "__main__":
    unittest.main()
