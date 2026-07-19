"""Append-only instrument registry and broker-symbol mapping repository."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from src.multimarket.models import Instrument

from .repository import SQLiteRepository


def _decode(row) -> Instrument:
    return Instrument.new(
        instrument_id=row["instrument_id"], exchange=row["exchange"], segment=row["segment"],
        symbol=row["symbol"], trading_symbol=row["trading_symbol"], isin=row["isin"], expiry=row["expiry"],
        strike=row["strike"], option_type=row["option_type"], lot_size=int(row["lot_size"]),
        tick_size=float(row["tick_size"]), currency=row["currency"], margin_group=row["margin_group"],
        status=row["status"], metadata=json.loads(row["metadata_json"]), created_at=row["created_at"],
        created_by=row["created_by"],
    )


class InstrumentRepository(SQLiteRepository):
    def insert(self, instrument: Instrument) -> Instrument:
        existing = self.find(instrument.exchange, instrument.segment, instrument.trading_symbol,
                             instrument.expiry, instrument.strike, instrument.option_type)
        if existing:
            return existing
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO instruments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (instrument.instrument_id, instrument.exchange, instrument.segment, instrument.symbol,
                 instrument.trading_symbol, instrument.isin, instrument.expiry, instrument.strike,
                 instrument.option_type, instrument.lot_size, instrument.tick_size, instrument.currency,
                 instrument.margin_group, instrument.status,
                 json.dumps(dict(instrument.metadata), sort_keys=True, separators=(",", ":")),
                 instrument.created_at, instrument.created_by),
            )
        return instrument

    def get(self, instrument_id: str) -> Instrument | None:
        row = self.connection.execute("SELECT * FROM instruments WHERE instrument_id=?", (instrument_id,)).fetchone()
        return _decode(row) if row else None

    def find(self, exchange, segment, trading_symbol, expiry=None, strike=None, option_type=None):
        row = self.connection.execute(
            "SELECT * FROM instruments WHERE exchange=? AND segment=? AND trading_symbol=? "
            "AND expiry IS ? AND strike IS ? AND option_type IS ?",
            (exchange, segment, trading_symbol, expiry, strike, option_type),
        ).fetchone()
        return _decode(row) if row else None

    def add_symbol_mapping(self, instrument_id: str, broker_name: str, broker_symbol: str,
                           broker_token: str | None = None, mapping_id: str | None = None) -> str:
        mapping_id = mapping_id or str(uuid4())
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO symbol_mappings VALUES (?, ?, ?, ?, ?, ?, ?)",
                (mapping_id, instrument_id, broker_name, broker_symbol, broker_token,
                 datetime.now(timezone.utc).isoformat(), "InstrumentRegistry"),
            )
        row = self.connection.execute(
            "SELECT mapping_id FROM symbol_mappings WHERE instrument_id=? AND broker_name=?",
            (instrument_id, broker_name),
        ).fetchone()
        return row["mapping_id"]

    def get_for_instrument(self, instrument_id: str, broker_name: str):
        row = self.connection.execute(
            "SELECT instrument_id, broker_name, broker_symbol, broker_token FROM symbol_mappings "
            "WHERE instrument_id=? AND broker_name=?", (instrument_id, broker_name),
        ).fetchone()
        return dict(row) if row else None

    def get_for_broker_symbol(self, broker_name: str, broker_symbol: str):
        row = self.connection.execute(
            "SELECT instrument_id, broker_name, broker_symbol, broker_token FROM symbol_mappings "
            "WHERE broker_name=? AND broker_symbol=?", (broker_name, broker_symbol),
        ).fetchone()
        return dict(row) if row else None
