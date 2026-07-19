"""CQRP research schema migrations."""

from __future__ import annotations

import sqlite3

from .migration import Migration


def _create_research_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategy_profiles (
            profile_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            coa_engine_version TEXT NOT NULL,
            validation_engine_version TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS market_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            captured_at TEXT NOT NULL,
            instrument TEXT NOT NULL,
            spot REAL NOT NULL,
            market_source TEXT NOT NULL,
            strategy_profile_id TEXT,
            scenario_number INTEGER,
            scenario TEXT,
            risk_mode TEXT,
            support REAL,
            resistance REAL,
            eos REAL,
            eor REAL,
            coa_payload_json TEXT NOT NULL,
            option_chain_json TEXT,
            data_quality_status TEXT NOT NULL,
            source_latency_ms INTEGER,
            FOREIGN KEY (strategy_profile_id) REFERENCES strategy_profiles(profile_id)
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_instrument_time
            ON market_snapshots(instrument, captured_at);
        CREATE INDEX IF NOT EXISTS idx_snapshots_scenario
            ON market_snapshots(scenario_number, captured_at);

        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            action TEXT NOT NULL,
            suggested_strike REAL,
            entry_level REAL,
            stop_level REAL,
            target_level REAL,
            confidence_score REAL,
            trade_allowed INTEGER NOT NULL,
            strategy_profile_id TEXT,
            rationale_json TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES market_snapshots(snapshot_id),
            FOREIGN KEY (strategy_profile_id) REFERENCES strategy_profiles(profile_id)
        );
        CREATE INDEX IF NOT EXISTS idx_signals_snapshot ON signals(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_signals_instrument_time
            ON signals(instrument, created_at);

        CREATE TABLE IF NOT EXISTS signal_validations (
            validation_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            category TEXT NOT NULL,
            score REAL,
            passed INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
        );
        CREATE INDEX IF NOT EXISTS idx_validations_signal ON signal_validations(signal_id);

        CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            strike REAL,
            quantity INTEGER NOT NULL,
            entry_spot REAL NOT NULL,
            entry_option_price REAL,
            stop_level REAL,
            target_level REAL,
            strategy_profile_id TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals(signal_id),
            FOREIGN KEY (strategy_profile_id) REFERENCES strategy_profiles(profile_id)
        );
        CREATE INDEX IF NOT EXISTS idx_paper_trades_signal ON paper_trades(signal_id);

        CREATE TABLE IF NOT EXISTS trade_updates (
            update_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            spot REAL NOT NULL,
            option_price REAL,
            unrealized_pnl REAL,
            scenario TEXT,
            coa2_state TEXT,
            mae REAL,
            mfe REAL,
            event_payload_json TEXT NOT NULL,
            FOREIGN KEY (trade_id) REFERENCES paper_trades(trade_id)
        );
        CREATE INDEX IF NOT EXISTS idx_trade_updates_trade_time
            ON trade_updates(trade_id, observed_at);

        CREATE TABLE IF NOT EXISTS trade_exits (
            exit_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL UNIQUE,
            exited_at TEXT NOT NULL,
            exit_spot REAL NOT NULL,
            exit_option_price REAL,
            realized_pnl REAL,
            exit_reason TEXT NOT NULL,
            holding_seconds INTEGER,
            event_payload_json TEXT NOT NULL,
            FOREIGN KEY (trade_id) REFERENCES paper_trades(trade_id)
        );

        CREATE TABLE IF NOT EXISTS system_events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            instrument TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_system_events_type_time
            ON system_events(event_type, occurred_at);
        """
    )

    immutable_tables = (
        "strategy_profiles", "market_snapshots", "signals", "signal_validations",
        "paper_trades", "trade_updates", "trade_exits", "system_events",
    )
    for table in immutable_tables:
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update "
            f"BEFORE UPDATE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, '{table} is append-only'); END"
        )
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete "
            f"BEFORE DELETE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, '{table} is append-only'); END"
        )


RESEARCH_MIGRATIONS = (
    Migration(version=1, name="research_schema_v1", apply=_create_research_schema),
)
