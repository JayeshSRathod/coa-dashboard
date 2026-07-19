"""Append-only repository abstractions for advanced portfolio analytics."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from .repository import SQLiteRepository


class _AnalyticsRepository(SQLiteRepository):
    table = ""
    def append(self, *, subject_id: str, payload: dict, fingerprint: str) -> str:
        row = self.connection.execute(f"SELECT analysis_id FROM {self.table} WHERE fingerprint=?", (fingerprint,)).fetchone()
        if row: return row["analysis_id"]
        analysis_id = str(uuid4())
        with self.connection:
            self.connection.execute(f"INSERT INTO {self.table} VALUES (?, ?, ?, ?, ?)",
                (analysis_id, subject_id, json.dumps(payload, sort_keys=True, default=str), fingerprint,
                 datetime.now(timezone.utc).isoformat()))
        return analysis_id
    def list(self, subject_id=None):
        query="SELECT * FROM "+self.table; values=[]
        if subject_id: query+=" WHERE subject_id=?"; values.append(subject_id)
        return [dict(row) | {"payload": json.loads(row["payload_json"])}
                for row in self.connection.execute(query+" ORDER BY created_at, analysis_id", values).fetchall()]


class PortfolioAnalyticsRepository(_AnalyticsRepository): table="portfolio_analytics"
class PositionAnalyticsRepository(_AnalyticsRepository): table="position_analytics"
class GreeksRepository(_AnalyticsRepository): table="greeks_analytics"
class OptionChainRepository(_AnalyticsRepository): table="option_chain_analytics"
class IVRepository(_AnalyticsRepository): table="iv_analytics"
class StressTestRepository(_AnalyticsRepository): table="stress_test_analytics"
class StrategyAnalyticsRepository(_AnalyticsRepository): table="strategy_analytics"
