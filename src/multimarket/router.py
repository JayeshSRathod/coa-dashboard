"""Deterministic account and broker route selection without broker invocation."""

from __future__ import annotations

import logging

from src.research.observability import emit_snapshot_event

from .models import RoutingDecision


class ExecutionRouter:
    def __init__(self, route_repository, account_repository, logger: logging.Logger | None = None) -> None:
        self.route_repository, self.account_repository = route_repository, account_repository
        self.logger = logger or logging.getLogger("cqrp.execution_router")

    def select(self, portfolio_id: str, *, preferred_broker: str | None = None) -> RoutingDecision:
        for route in self.route_repository.list_for_portfolio(portfolio_id):
            if preferred_broker and route.broker_name != preferred_broker:
                continue
            account = self.account_repository.get(route.account_id)
            if account and account.status == "ACTIVE" and account.execution_enabled:
                decision = RoutingDecision(portfolio_id, account.account_id, route.broker_name, route.route_id,
                                           "highest-priority eligible route")
                emit_snapshot_event(self.logger, "execution_route_selected", portfolio_id=portfolio_id,
                                    account_id=account.account_id, broker=route.broker_name)
                return decision
        decision = RoutingDecision(portfolio_id, None, None, None, "no eligible execution route")
        emit_snapshot_event(self.logger, "execution_route_unavailable", portfolio_id=portfolio_id)
        return decision
