"""Read-only broker synchronization service with append-only mismatch evidence."""

from __future__ import annotations

import logging

from src.persistence.broker_sync_repository import BrokerSyncRepository
from src.research.observability import emit_snapshot_event

from .brokers import BrokerAdapter


class BrokerSynchronizationService:
    def __init__(self, adapter: BrokerAdapter, repository: BrokerSyncRepository,
                 logger: logging.Logger | None = None) -> None:
        self.adapter, self.repository = adapter, repository
        self.logger = logger or logging.getLogger("cqrp.broker_sync")

    def synchronize(self) -> dict:
        try:
            payload = {
                "positions": self.adapter.get_positions(), "holdings": self.adapter.get_holdings(),
                "funds": self.adapter.get_funds(), "trades": self.adapter.get_trades(),
            }
            sync_id = self.repository.append(
                broker_name=self.adapter.name, sync_type="ACCOUNT", status="SUCCESS", payload=payload
            )
            emit_snapshot_event(self.logger, "broker_sync_completed", broker=self.adapter.name, sync_id=sync_id)
            return {"sync_id": sync_id, **payload}
        except Exception as exc:
            sync_id = self.repository.append(
                broker_name=self.adapter.name, sync_type="ACCOUNT", status="FAILED",
                payload={"error_type": type(exc).__name__},
            )
            emit_snapshot_event(self.logger, "broker_sync_failed", broker=self.adapter.name, sync_id=sync_id)
            return {"sync_id": sync_id, "error": type(exc).__name__}
