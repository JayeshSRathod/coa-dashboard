"""Multi-account, read-only synchronization and unified position aggregation."""

from __future__ import annotations

import logging

from src.multimarket.aggregation import aggregate_positions
from src.research.observability import emit_snapshot_event


class MultiBrokerSynchronizationService:
    def __init__(self, account_repository, broker_sync_repository, catalog, logger: logging.Logger | None = None) -> None:
        self.account_repository = account_repository
        self.broker_sync_repository = broker_sync_repository
        self.catalog = catalog
        self.logger = logger or logging.getLogger("cqrp.multi_broker_sync")

    def synchronize_accounts(self, accounts) -> dict:
        position_sets, results = [], []
        for account in accounts:
            adapter = self.catalog.get(account.broker_name)
            if not adapter:
                results.append({"account_id": account.account_id, "status": "NO_ADAPTER"})
                continue
            try:
                positions = adapter.get_positions()
                sync_id = self.broker_sync_repository.append(
                    broker_name=account.broker_name, sync_type="POSITIONS", status="SUCCESS",
                    payload={"account_id": account.account_id, "positions": positions},
                )
                position_sets.append((account.broker_name, account.account_id, positions))
                results.append({"account_id": account.account_id, "status": "SUCCESS", "sync_id": sync_id})
            except Exception as exc:
                sync_id = self.broker_sync_repository.append(
                    broker_name=account.broker_name, sync_type="POSITIONS", status="FAILED",
                    payload={"account_id": account.account_id, "error_type": type(exc).__name__},
                )
                results.append({"account_id": account.account_id, "status": "FAILED", "sync_id": sync_id})
        aggregate = aggregate_positions(position_sets)
        emit_snapshot_event(self.logger, "multi_broker_sync_completed",
                            accounts=len(results), instruments=len(aggregate))
        return {"accounts": results, "positions": aggregate}
