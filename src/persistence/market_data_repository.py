"""Append-only persistence for Sprint-019 market-data platform records."""

from __future__ import annotations

import json
from typing import Any

from src.market_data.models import OptionChainSnapshot, ProviderHealth, SourceTransition

from .repository import SQLiteRepository


def _json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


class MarketDataRepository(SQLiteRepository):
    def append_snapshot(self, snapshot: OptionChainSnapshot) -> str:
        with self.connection:
            self.connection.execute("INSERT INTO market_snapshot (snapshot_id, instrument_id, provider, captured_at, spot, expiry, quality_state, latency_ms, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (snapshot.snapshot_id, snapshot.instrument_id, snapshot.provider, snapshot.captured_at, snapshot.spot, snapshot.expiry, snapshot.quality.value, snapshot.latency_ms, _json(snapshot.as_dict())))
        return snapshot.snapshot_id

    def append_health(self, health: ProviderHealth) -> str:
        health_id = f"{health.provider}:{health.observed_at}"
        with self.connection:
            self.connection.execute("INSERT INTO provider_health (health_id, provider, observed_at, availability, latency_ms, error_count, heartbeat_at, circuit_state, details_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (health_id, health.provider, health.observed_at, health.availability.value, health.latency_ms, health.error_count, health.heartbeat_at, health.circuit_state.value, _json(health.details)))
        return health_id

    def append_transition(self, transition: SourceTransition) -> str:
        with self.connection:
            self.connection.execute("INSERT INTO source_transition (transition_id, instrument_id, from_provider, to_provider, reason, occurred_at) VALUES (?, ?, ?, ?, ?, ?)", (transition.transition_id, transition.instrument_id, transition.from_provider, transition.to_provider, transition.reason, transition.occurred_at))
        return transition.transition_id

    def append_event(self, provider: str, event_type: str, occurred_at: str, details: dict[str, Any]) -> str:
        event_id = f"{provider}:{event_type}:{occurred_at}"
        with self.connection:
            self.connection.execute("INSERT INTO provider_events (event_id, provider, event_type, occurred_at, details_json) VALUES (?, ?, ?, ?, ?)", (event_id, provider, event_type, occurred_at, _json(details)))
        return event_id

    def latest_snapshot(self, instrument_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM market_snapshot WHERE instrument_id = ? ORDER BY captured_at DESC, snapshot_id DESC LIMIT 1", (instrument_id,)).fetchone()
        return _decode(row) if row else None

    def list_snapshots(self, instrument_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        query, values = "SELECT * FROM market_snapshot WHERE instrument_id = ?", [instrument_id]
        if start is not None: query, values = query + " AND captured_at >= ?", values + [start]
        if end is not None: query, values = query + " AND captured_at <= ?", values + [end]
        rows = self.connection.execute(query + " ORDER BY captured_at ASC, snapshot_id ASC", values).fetchall()
        return [_decode(row) for row in rows]

    def latest_health(self, provider: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM provider_health"
        values: list[Any] = []
        if provider: query, values = query + " WHERE provider = ?", [provider]
        rows = self.connection.execute(query + " ORDER BY observed_at DESC").fetchall()
        seen, latest = set(), []
        for row in rows:
            item = dict(row)
            if item["provider"] not in seen:
                latest.append(_decode_health(item)); seen.add(item["provider"])
        return latest

    def list_transitions(self, instrument_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM source_transition WHERE instrument_id = ? ORDER BY occurred_at ASC, transition_id ASC", (instrument_id,)).fetchall()
        return [dict(row) for row in rows]


def _decode(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json"))
    return item


def _decode_health(item: dict[str, Any]) -> dict[str, Any]:
    item["details"] = json.loads(item.pop("details_json"))
    return item
