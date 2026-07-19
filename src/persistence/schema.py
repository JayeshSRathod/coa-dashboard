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


def _add_market_capture_fields(connection: sqlite3.Connection) -> None:
    """Add replay metadata without rewriting any historical snapshot."""
    for statement in (
        "ALTER TABLE market_snapshots ADD COLUMN session_id TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN market_captured_at TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN ingested_at TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN futures_price REAL",
        "ALTER TABLE market_snapshots ADD COLUMN atm_strike REAL",
        "ALTER TABLE market_snapshots ADD COLUMN expiry TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN expiry_type TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN data_completeness REAL",
        "ALTER TABLE market_snapshots ADD COLUMN is_complete INTEGER",
        "ALTER TABLE market_snapshots ADD COLUMN missing_strikes_json TEXT",
        "ALTER TABLE market_snapshots ADD COLUMN metadata_json TEXT",
    ):
        connection.execute(statement)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_snapshots_session_time "
        "ON market_snapshots(session_id, market_captured_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_snapshots_replay_time "
        "ON market_snapshots(instrument, market_captured_at)"
    )


def _add_coa_result_store(connection: sqlite3.Connection) -> None:
    """Add immutable COA research outputs without rewriting historical data."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS coa_results (
            coa_result_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            experiment_id TEXT,
            experiment_key TEXT NOT NULL DEFAULT '',
            strategy_version TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            scenario_number INTEGER,
            scenario TEXT,
            eos REAL,
            eor REAL,
            support REAL,
            resistance REAL,
            momentum_json TEXT,
            diversion_json TEXT,
            trend TEXT,
            direction TEXT,
            risk_mode TEXT,
            raw_output_json TEXT NOT NULL,
            processing_time_ms REAL NOT NULL,
            market_timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES market_snapshots(snapshot_id),
            UNIQUE (snapshot_id, engine_version, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_coa_results_snapshot
            ON coa_results(snapshot_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_coa_results_session_time
            ON coa_results(session_id, market_timestamp, coa_result_id);

        CREATE TRIGGER IF NOT EXISTS coa_results_no_update
            BEFORE UPDATE ON coa_results BEGIN
            SELECT RAISE(ABORT, 'coa_results is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS coa_results_no_delete
            BEFORE DELETE ON coa_results BEGIN
            SELECT RAISE(ABORT, 'coa_results is append-only');
            END;
        """
    )


def _add_validation_result_store(connection: sqlite3.Connection) -> None:
    """Add append-only validation evidence for persisted COA research results."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS validation_results (
            validation_id TEXT PRIMARY KEY,
            coa_result_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            experiment_id TEXT,
            experiment_key TEXT NOT NULL DEFAULT '',
            strategy_version TEXT NOT NULL,
            validation_version TEXT NOT NULL,
            volume_score REAL NOT NULL,
            oi_score REAL NOT NULL,
            strike_score REAL NOT NULL,
            liquidity_score REAL NOT NULL,
            market_context_score REAL NOT NULL,
            historical_score REAL,
            overall_score REAL NOT NULL,
            confidence_band TEXT NOT NULL,
            is_valid INTEGER NOT NULL,
            failure_reasons_json TEXT NOT NULL,
            warning_reasons_json TEXT NOT NULL,
            scoring_details_json TEXT NOT NULL,
            processing_time_ms REAL NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (coa_result_id) REFERENCES coa_results(coa_result_id),
            FOREIGN KEY (snapshot_id) REFERENCES market_snapshots(snapshot_id),
            UNIQUE (coa_result_id, validation_version, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_validation_results_coa
            ON validation_results(coa_result_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_validation_results_snapshot
            ON validation_results(snapshot_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_validation_results_session
            ON validation_results(session_id, created_at, validation_id);

        CREATE TRIGGER IF NOT EXISTS validation_results_no_update
            BEFORE UPDATE ON validation_results BEGIN
            SELECT RAISE(ABORT, 'validation_results is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS validation_results_no_delete
            BEFORE DELETE ON validation_results BEGIN
            SELECT RAISE(ABORT, 'validation_results is append-only');
            END;
        """
    )


def _add_research_signal_store(connection: sqlite3.Connection) -> None:
    """Add immutable, non-executable research signal recommendations."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS research_signals (
            signal_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            coa_result_id TEXT NOT NULL,
            validation_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            experiment_id TEXT,
            experiment_key TEXT NOT NULL DEFAULT '',
            strategy_version TEXT NOT NULL,
            signal_version TEXT NOT NULL,
            instrument TEXT NOT NULL,
            expiry TEXT,
            signal_type TEXT NOT NULL,
            signal_state TEXT NOT NULL,
            direction TEXT,
            entry_price REAL,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            trailing_reference REAL,
            confidence_score REAL NOT NULL,
            confidence_band TEXT NOT NULL,
            scenario TEXT,
            eos REAL,
            eor REAL,
            momentum_json TEXT,
            diversion_json TEXT,
            reasons_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            details_json TEXT NOT NULL,
            processing_time_ms REAL NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES market_snapshots(snapshot_id),
            FOREIGN KEY (coa_result_id) REFERENCES coa_results(coa_result_id),
            FOREIGN KEY (validation_id) REFERENCES validation_results(validation_id),
            UNIQUE (validation_id, signal_version, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_research_signals_snapshot
            ON research_signals(snapshot_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_research_signals_session
            ON research_signals(session_id, created_at, signal_id);
        CREATE INDEX IF NOT EXISTS idx_research_signals_confidence
            ON research_signals(confidence_score, created_at);

        CREATE TRIGGER IF NOT EXISTS research_signals_no_update
            BEFORE UPDATE ON research_signals BEGIN
            SELECT RAISE(ABORT, 'research_signals is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_signals_no_delete
            BEFORE DELETE ON research_signals BEGIN
            SELECT RAISE(ABORT, 'research_signals is append-only');
            END;
        """
    )

RESEARCH_MIGRATIONS = (
    Migration(version=1, name="research_schema_v1", apply=_create_research_schema),
    Migration(version=2, name="market_snapshot_capture_v2", apply=_add_market_capture_fields),
    Migration(version=3, name="coa_research_results_v3", apply=_add_coa_result_store),
    Migration(version=4, name="validation_evidence_v4", apply=_add_validation_result_store),
    Migration(version=5, name="research_signals_v5", apply=_add_research_signal_store),
)
