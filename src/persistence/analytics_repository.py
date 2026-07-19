"""Read-model repository for analytics source data; execution writes are prohibited."""

from __future__ import annotations

from src.execution.models import PaperTrade

from .trade_repository import _decode
from .repository import SQLiteRepository


class AnalyticsRepository(SQLiteRepository):
    """Provide indexed, ordered source identities for historical performance calculations."""

    def list_trades(
        self, *, session_id: str | None = None, experiment_id: str | None = None,
        strategy_version: str | None = None,
    ) -> list[PaperTrade]:
        clauses, values = [], []
        if session_id is not None:
            clauses.append("session_id = ?"); values.append(session_id)
        if experiment_id is not None:
            clauses.append("experiment_id = ?"); values.append(experiment_id)
        if strategy_version is not None:
            clauses.append("strategy_version = ?"); values.append(strategy_version)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            "SELECT * FROM simulated_trades" + where + " ORDER BY created_at ASC, trade_id ASC", values
        ).fetchall()
        return [_decode(row) for row in rows]
