"""Append-only portfolio-to-account routing repository."""

from __future__ import annotations

from src.multimarket.models import ExecutionRoute

from .repository import SQLiteRepository


class ExecutionRouteRepository(SQLiteRepository):
    def insert(self, route: ExecutionRoute) -> ExecutionRoute:
        existing = self.connection.execute(
            "SELECT route_id FROM execution_routes WHERE portfolio_id=? AND account_id=?",
            (route.portfolio_id, route.account_id),
        ).fetchone()
        if existing:
            return self.get(existing["route_id"])
        with self.connection:
            self.connection.execute("INSERT INTO execution_routes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (route.route_id, route.portfolio_id, route.account_id, route.broker_name, route.priority,
                 int(route.enabled), route.created_at, route.created_by))
        return route

    def get(self, route_id):
        row = self.connection.execute("SELECT * FROM execution_routes WHERE route_id=?", (route_id,)).fetchone()
        return ExecutionRoute.new(**dict(row)) if row else None

    def list_for_portfolio(self, portfolio_id):
        rows = self.connection.execute(
            "SELECT * FROM execution_routes WHERE portfolio_id=? AND enabled=1 ORDER BY priority, route_id",
            (portfolio_id,),
        ).fetchall()
        return [ExecutionRoute.new(**dict(row)) for row in rows]
