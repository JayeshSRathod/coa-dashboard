"""Append-only persistence boundary for broker-gateway order identities."""

from __future__ import annotations

from src.live_execution.models import ExecutionOrder

from .repository import SQLiteRepository


def _decode(row) -> ExecutionOrder:
    return ExecutionOrder.new(
        order_id=row["order_id"], execution_id=row["execution_id"], broker_order_id=row["broker_order_id"],
        client_order_key=row["client_order_key"], signal_id=row["signal_id"], trade_id=row["trade_id"],
        portfolio_id=row["portfolio_id"], broker_name=row["broker_name"], execution_mode=row["execution_mode"],
        exchange=row["exchange"], symbol=row["symbol"], expiry=row["expiry"], strike=row["strike"],
        option_type=row["option_type"], order_type=row["order_type"], product_type=row["product_type"],
        transaction_type=row["transaction_type"], quantity=int(row["quantity"]), price=row["price"],
        trigger_price=row["trigger_price"], created_at=row["created_at"], created_by=row["created_by"],
    )


class OrderRepository(SQLiteRepository):
    def insert(self, order: ExecutionOrder) -> ExecutionOrder:
        existing = self.get_by_client_key(order.client_order_key)
        if existing:
            return existing
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_orders (
                    order_id, execution_id, broker_order_id, client_order_key, signal_id, trade_id,
                    portfolio_id, broker_name, execution_mode, exchange, symbol, expiry, strike,
                    option_type, order_type, product_type, transaction_type, quantity, price,
                    trigger_price, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order.order_id, order.execution_id, order.broker_order_id, order.client_order_key,
                 order.signal_id, order.trade_id, order.portfolio_id, order.broker_name,
                 order.execution_mode, order.exchange, order.symbol, order.expiry, order.strike,
                 order.option_type, order.order_type, order.product_type, order.transaction_type,
                 order.quantity, order.price, order.trigger_price, order.created_at, order.created_by),
            )
        return order

    def get(self, order_id: str) -> ExecutionOrder | None:
        row = self.connection.execute(
            "SELECT * FROM execution_orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return _decode(row) if row else None

    def get_by_client_key(self, client_order_key: str) -> ExecutionOrder | None:
        row = self.connection.execute(
            "SELECT * FROM execution_orders WHERE client_order_key = ?", (client_order_key,)
        ).fetchone()
        return _decode(row) if row else None
