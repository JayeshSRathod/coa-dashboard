import unittest
from datetime import datetime

from src.live_execution.brokers import DhanBrokerAdapter
from src.live_execution.config import ExecutionConfig
from src.live_execution.gateway import ExecutionGateway
from src.live_execution.models import OrderRequest
from src.live_execution.projector import project_order
from src.persistence.connection import connect
from src.persistence.execution_repository import ExecutionRepository
from src.persistence.migration import apply_migrations
from src.persistence.order_event_repository import OrderEventRepository
from src.persistence.order_repository import OrderRepository
from src.persistence.schema import RESEARCH_MIGRATIONS


class FakeBroker:
    name = "fake"

    def __init__(self, failures=0):
        self.failures, self.calls = failures, 0

    def place_order(self, request):
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError()
        return {"id": "BROKER-1"}

    def modify_order(self, broker_order_id, changes): return {}
    def cancel_order(self, broker_order_id): return {}
    def get_order(self, broker_order_id): return {}
    def get_positions(self): return []
    def get_holdings(self): return []
    def get_funds(self): return {}
    def get_trades(self): return []


def request(key="key-1"):
    return OrderRequest(
        client_order_key=key, signal_id=None, trade_id=None, portfolio_id="p1",
        approval_reference="risk-approval-1", broker_name="fake", exchange="NSE",
        symbol="NSE:NIFTY", transaction_type="BUY", quantity=2, price=100.0,
        estimated_value=200.0,
    )


class ExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        connection = connect(":memory:")
        apply_migrations(connection, RESEARCH_MIGRATIONS)
        self.orders = OrderRepository(connection)
        self.events = OrderEventRepository(connection)
        self.execution = ExecutionRepository(self.orders, self.events)

    def gateway(self, config, adapters=None):
        return ExecutionGateway(config, self.orders, self.events, self.execution, adapters or {}, sleeper=lambda _: None)

    def test_paper_mode_emits_filled_lifecycle(self):
        order = self.gateway(ExecutionConfig(execution_mode="PAPER")).submit(request())
        state = project_order(order, self.events.list_for_order(order.order_id))
        self.assertEqual(state.status, "FILLED")
        self.assertEqual(state.filled_quantity, 2)

    def test_disabled_mode_never_calls_broker(self):
        broker = FakeBroker()
        order = self.gateway(ExecutionConfig(), {"fake": broker}).submit(request())
        state = project_order(order, self.events.list_for_order(order.order_id))
        self.assertEqual(state.status, "REJECTED")
        self.assertEqual(broker.calls, 0)

    def test_duplicate_client_key_is_idempotent(self):
        gateway = self.gateway(ExecutionConfig(execution_mode="PAPER"))
        first, second = gateway.submit(request()), gateway.submit(request())
        self.assertEqual(first.order_id, second.order_id)

    def test_live_mode_safety_blocks_and_retry_is_controlled(self):
        broker = FakeBroker()
        blocked = self.gateway(
            ExecutionConfig(execution_mode="LIVE", trading_enabled=False, kill_switch=False, dry_run=False),
            {"fake": broker},
        ).submit(request(), now=datetime(2026, 7, 19, 10, 0))
        self.assertEqual(project_order(blocked, self.events.list_for_order(blocked.order_id)).status, "REJECTED")
        self.assertEqual(broker.calls, 0)

        retrying = FakeBroker(failures=1)
        live = self.gateway(
            ExecutionConfig(execution_mode="LIVE", trading_enabled=True, kill_switch=False, dry_run=False),
            {"fake": retrying},
        ).submit(request("key-2"), now=datetime(2026, 7, 19, 10, 0))
        self.assertEqual(retrying.calls, 2)
        self.assertEqual(project_order(live, self.events.list_for_order(live.order_id)).status, "ACKNOWLEDGED")

    def test_framework_adapter_is_explicitly_unsupported(self):
        with self.assertRaises(NotImplementedError):
            DhanBrokerAdapter().get_funds()


if __name__ == "__main__":
    unittest.main()
