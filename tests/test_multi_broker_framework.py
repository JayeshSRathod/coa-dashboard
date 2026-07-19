import unittest

from src.multimarket.aggregation import aggregate_positions
from src.multimarket.brokers import AngelOneBrokerAdapter, DhanBrokerAdapter
from src.multimarket.models import BrokerAccount, ExecutionRoute, Instrument
from src.multimarket.providers import CallableMarketDataProvider
from src.multimarket.router import ExecutionRouter
from src.multimarket.translation import SymbolTranslator
from src.persistence.broker_account_repository import BrokerAccountRepository
from src.persistence.connection import connect
from src.persistence.execution_route_repository import ExecutionRouteRepository
from src.persistence.instrument_repository import InstrumentRepository
from src.persistence.migration import apply_migrations
from src.persistence.schema import RESEARCH_MIGRATIONS


class MultiBrokerFrameworkTests(unittest.TestCase):
    def setUp(self):
        connection = connect(":memory:")
        apply_migrations(connection, RESEARCH_MIGRATIONS)
        self.instruments = InstrumentRepository(connection)
        self.accounts = BrokerAccountRepository(connection)
        self.routes = ExecutionRouteRepository(connection)

    def test_instrument_registry_and_symbol_translation_are_deterministic(self):
        instrument = Instrument.new(
            instrument_id="nifty-option", exchange="NSE", segment="OPTIDX", symbol="NIFTY",
            trading_symbol="NIFTY25JUL25000CE", expiry="2026-07-23", strike=25000.0,
            option_type="CE", lot_size=75, tick_size=0.05, currency="INR", status="ACTIVE",
        )
        first = self.instruments.insert(instrument)
        duplicate = self.instruments.insert(instrument)
        self.assertEqual(first.instrument_id, duplicate.instrument_id)
        self.instruments.add_symbol_mapping(first.instrument_id, "fyers", "NSE:NIFTY2572525000CE")
        translator = SymbolTranslator(self.instruments)
        self.assertEqual(translator.to_broker(first.instrument_id, "fyers").broker_symbol,
                         "NSE:NIFTY2572525000CE")
        self.assertEqual(translator.to_instrument_id("fyers", "NSE:NIFTY2572525000CE"), first.instrument_id)

    def test_router_selects_highest_priority_eligible_account(self):
        account = self.accounts.insert(BrokerAccount.new(
            account_id="account-1", broker_name="fyers", client_id="client-1", display_name="Primary",
            status="ACTIVE", execution_enabled=True,
        ))
        self.routes.insert(ExecutionRoute.new(
            route_id="route-1", portfolio_id="portfolio-1", account_id=account.account_id,
            broker_name="fyers", priority=1,
        ))
        decision = ExecutionRouter(self.routes, self.accounts).select("portfolio-1")
        self.assertEqual(decision.account_id, "account-1")
        self.assertEqual(decision.broker_name, "fyers")

    def test_provider_and_cross_broker_aggregation(self):
        provider = CallableMarketDataProvider("replay", lambda instrument_id: {
            "instrument_id": instrument_id, "spot": 100.0
        })
        self.assertEqual(provider.snapshot("nifty")["spot"], 100.0)
        positions = aggregate_positions([
            ("fyers", "a1", [{"instrument_id": "nifty", "quantity": 2, "net_value": 200}]),
            ("dhan", "a2", [{"instrument_id": "nifty", "quantity": -1, "net_value": -100}]),
        ])
        self.assertEqual(positions[0]["quantity"], 1.0)
        self.assertEqual(positions[0]["net_value"], 100.0)

    def test_unimplemented_brokers_remain_contract_safe(self):
        for adapter in (DhanBrokerAdapter(), AngelOneBrokerAdapter()):
            with self.assertRaises(NotImplementedError):
                adapter.get_funds()


if __name__ == "__main__":
    unittest.main()
