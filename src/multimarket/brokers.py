"""Multi-broker adapter catalog built on the Sprint-010 execution contract."""

from __future__ import annotations

from src.live_execution.brokers import (
    BrokerAdapter,
    DhanBrokerAdapter,
    FyersBrokerAdapter,
    UnsupportedBrokerAdapter,
    ZerodhaBrokerAdapter,
)


class AngelOneBrokerAdapter(UnsupportedBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("angel_one")


class UpstoxBrokerAdapter(UnsupportedBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("upstox")


class AliceBlueBrokerAdapter(UnsupportedBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("alice_blue")


class BrokerCatalog:
    """Explicit adapter registration; no automatic broker failover is performed."""

    def __init__(self, adapters: dict[str, BrokerAdapter] | None = None) -> None:
        self._adapters = dict(adapters or {})

    def register(self, adapter: BrokerAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, broker_name: str) -> BrokerAdapter | None:
        return self._adapters.get(broker_name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
