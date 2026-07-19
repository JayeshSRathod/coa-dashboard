"""Symbol translation boundary; research code only handles internal instrument IDs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerSymbol:
    instrument_id: str
    broker_name: str
    broker_symbol: str
    broker_token: str | None = None


class SymbolTranslator:
    def __init__(self, mapping_repository) -> None:
        self.mapping_repository = mapping_repository

    def to_broker(self, instrument_id: str, broker_name: str) -> BrokerSymbol | None:
        mapping = self.mapping_repository.get_for_instrument(instrument_id, broker_name)
        return BrokerSymbol(**mapping) if mapping else None

    def to_instrument_id(self, broker_name: str, broker_symbol: str) -> str | None:
        mapping = self.mapping_repository.get_for_broker_symbol(broker_name, broker_symbol)
        return mapping["instrument_id"] if mapping else None
