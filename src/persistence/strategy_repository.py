"""Append-only registry for immutable strategy versions."""

from __future__ import annotations

from src.strategy_lab.models import Strategy
from .repository import SQLiteRepository


def _decode(row):
    return Strategy.new(**dict(row))


class StrategyRepository(SQLiteRepository):
    def insert(self, strategy: Strategy) -> Strategy:
        existing = self.get_by_name_version(strategy.strategy_name, strategy.version)
        if existing:
            return existing
        with self.connection:
            self.connection.execute("INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (strategy.strategy_id, strategy.strategy_name, strategy.description, strategy.owner,
                 strategy.category, strategy.asset_class, strategy.market, strategy.version, strategy.status,
                 strategy.parent_strategy_id, strategy.created_at, strategy.created_by))
        return strategy

    def get(self, strategy_id):
        row = self.connection.execute("SELECT * FROM strategies WHERE strategy_id=?", (strategy_id,)).fetchone()
        return _decode(row) if row else None

    def get_by_name_version(self, name, version):
        row = self.connection.execute("SELECT * FROM strategies WHERE strategy_name=? AND version=?",
                                      (name, version)).fetchone()
        return _decode(row) if row else None
