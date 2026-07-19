"""Repository for immutable simulated-trade identities."""

from __future__ import annotations

from src.execution.models import PaperTrade

from .repository import SQLiteRepository


def _decode(row):
    return PaperTrade.new(
        trade_id=row["trade_id"], signal_id=row["signal_id"], session_id=row["session_id"],
        snapshot_id=row["snapshot_id"], experiment_id=row["experiment_id"],
        strategy_version=row["strategy_version"], execution_version=row["execution_version"],
        instrument=row["instrument"], direction=row["direction"], expiry=row["expiry"],
        strike=row["strike"], option_type=row["option_type"], quantity=row["quantity"],
        intended_entry=row["intended_entry"], initial_stop_loss=row["initial_stop_loss"],
        initial_target_1=row["initial_target_1"], initial_target_2=row["initial_target_2"],
        initial_trailing_reference=row["initial_trailing_reference"],
        created_at=row["created_at"], created_by=row["created_by"],
    )


class TradeRepository(SQLiteRepository):
    def insert(self, trade: PaperTrade) -> PaperTrade:
        existing = self.get_by_signal(trade.signal_id, trade.execution_version, trade.experiment_id)
        if existing:
            return existing
        values = (trade.trade_id, trade.signal_id, trade.session_id, trade.snapshot_id,
                  trade.experiment_id, trade.experiment_id or "", trade.strategy_version,
                  trade.execution_version, trade.instrument, trade.direction, trade.expiry,
                  trade.strike, trade.option_type, trade.quantity, trade.intended_entry,
                  trade.initial_stop_loss, trade.initial_target_1, trade.initial_target_2,
                  trade.initial_trailing_reference, trade.created_at, trade.created_by)
        with self.connection:
            self.connection.execute(
                """INSERT INTO simulated_trades (
                trade_id, signal_id, session_id, snapshot_id, experiment_id, experiment_key,
                strategy_version, execution_version, instrument, direction, expiry, strike,
                option_type, quantity, intended_entry, initial_stop_loss, initial_target_1,
                initial_target_2, initial_trailing_reference, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", values)
        return trade

    def get(self, trade_id: str) -> PaperTrade | None:
        row=self.connection.execute("SELECT * FROM simulated_trades WHERE trade_id=?", (trade_id,)).fetchone()
        return _decode(row) if row else None

    def get_by_signal(self, signal_id, execution_version, experiment_id):
        row=self.connection.execute("SELECT * FROM simulated_trades WHERE signal_id=? AND execution_version=? AND experiment_key=?",
                                    (signal_id,execution_version,experiment_id or "")).fetchone()
        return _decode(row) if row else None

    def get_session_trades(self, session_id):
        return [_decode(row) for row in self.connection.execute("SELECT * FROM simulated_trades WHERE session_id=? ORDER BY created_at,trade_id",(session_id,)).fetchall()]

    def get_experiment_trades(self, experiment_id):
        return [_decode(row) for row in self.connection.execute("SELECT * FROM simulated_trades WHERE experiment_id=? ORDER BY created_at,trade_id",(experiment_id,)).fetchall()]
