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


def _add_paper_execution_store(connection: sqlite3.Connection) -> None:
    """Add event-sourced paper-trading identities and immutable lifecycle events."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS simulated_trades (
            trade_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            experiment_id TEXT,
            experiment_key TEXT NOT NULL DEFAULT '',
            strategy_version TEXT NOT NULL,
            execution_version TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            expiry TEXT,
            strike REAL,
            option_type TEXT,
            quantity INTEGER NOT NULL,
            intended_entry REAL,
            initial_stop_loss REAL,
            initial_target_1 REAL,
            initial_target_2 REAL,
            initial_trailing_reference REAL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (signal_id) REFERENCES research_signals(signal_id),
            FOREIGN KEY (snapshot_id) REFERENCES market_snapshots(snapshot_id),
            UNIQUE (signal_id, execution_version, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_simulated_trades_signal ON simulated_trades(signal_id);
        CREATE INDEX IF NOT EXISTS idx_simulated_trades_session ON simulated_trades(session_id, created_at);

        CREATE TABLE IF NOT EXISTS simulated_trade_events (
            event_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            source_snapshot_id TEXT,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            event_payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (trade_id) REFERENCES simulated_trades(trade_id),
            UNIQUE (trade_id, event_type, source_snapshot_id)
        );
        CREATE INDEX IF NOT EXISTS idx_simulated_trade_events_trade_time
            ON simulated_trade_events(trade_id, occurred_at, event_id);
        CREATE INDEX IF NOT EXISTS idx_simulated_trade_events_session_time
            ON simulated_trade_events(session_id, occurred_at, event_id);

        CREATE TRIGGER IF NOT EXISTS simulated_trades_no_update
            BEFORE UPDATE ON simulated_trades BEGIN
            SELECT RAISE(ABORT, 'simulated_trades is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS simulated_trades_no_delete
            BEFORE DELETE ON simulated_trades BEGIN
            SELECT RAISE(ABORT, 'simulated_trades is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS simulated_trade_events_no_update
            BEFORE UPDATE ON simulated_trade_events BEGIN
            SELECT RAISE(ABORT, 'simulated_trade_events is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS simulated_trade_events_no_delete
            BEFORE DELETE ON simulated_trade_events BEGIN
            SELECT RAISE(ABORT, 'simulated_trade_events is append-only');
            END;
        """
    )


def _add_portfolio_risk_store(connection: sqlite3.Connection) -> None:
    """Add append-only portfolios, risk decisions, capital events, and exposures."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id TEXT PRIMARY KEY, name TEXT NOT NULL, owner TEXT,
            initial_capital REAL NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS risk_decisions (
            decision_id TEXT PRIMARY KEY, signal_id TEXT NOT NULL, portfolio_id TEXT NOT NULL,
            experiment_id TEXT, experiment_key TEXT NOT NULL DEFAULT '', risk_version TEXT NOT NULL,
            decision TEXT NOT NULL, requested_quantity INTEGER NOT NULL, approved_quantity INTEGER NOT NULL,
            capital_required REAL NOT NULL, capital_available REAL NOT NULL, rejection_reason TEXT,
            risk_metrics_json TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL,
            FOREIGN KEY (signal_id) REFERENCES research_signals(signal_id),
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
            UNIQUE(signal_id, portfolio_id, risk_version, experiment_key)
        );
        CREATE INDEX IF NOT EXISTS idx_risk_decisions_portfolio ON risk_decisions(portfolio_id, created_at);
        CREATE TABLE IF NOT EXISTS portfolio_capital_events (
            event_id TEXT PRIMARY KEY, portfolio_id TEXT NOT NULL, decision_id TEXT,
            event_type TEXT NOT NULL, amount REAL NOT NULL, occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
            FOREIGN KEY (decision_id) REFERENCES risk_decisions(decision_id),
            UNIQUE(decision_id, event_type)
        );
        CREATE TABLE IF NOT EXISTS portfolio_exposures (
            exposure_id TEXT PRIMARY KEY, portfolio_id TEXT NOT NULL, source_snapshot_id TEXT,
            instrument TEXT, expiry TEXT, option_type TEXT, invested_amount REAL NOT NULL,
            total_risk REAL NOT NULL, open_positions INTEGER NOT NULL, realized_pnl REAL NOT NULL,
            unrealized_pnl REAL NOT NULL, total_equity REAL NOT NULL, max_drawdown REAL NOT NULL,
            payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
        );
        CREATE INDEX IF NOT EXISTS idx_portfolio_exposures_portfolio ON portfolio_exposures(portfolio_id, created_at);
        CREATE TRIGGER IF NOT EXISTS portfolios_no_update BEFORE UPDATE ON portfolios BEGIN SELECT RAISE(ABORT, 'portfolios is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS portfolios_no_delete BEFORE DELETE ON portfolios BEGIN SELECT RAISE(ABORT, 'portfolios is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS risk_decisions_no_update BEFORE UPDATE ON risk_decisions BEGIN SELECT RAISE(ABORT, 'risk_decisions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS risk_decisions_no_delete BEFORE DELETE ON risk_decisions BEGIN SELECT RAISE(ABORT, 'risk_decisions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS portfolio_capital_events_no_update BEFORE UPDATE ON portfolio_capital_events BEGIN SELECT RAISE(ABORT, 'portfolio_capital_events is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS portfolio_capital_events_no_delete BEFORE DELETE ON portfolio_capital_events BEGIN SELECT RAISE(ABORT, 'portfolio_capital_events is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS portfolio_exposures_no_update BEFORE UPDATE ON portfolio_exposures BEGIN SELECT RAISE(ABORT, 'portfolio_exposures is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS portfolio_exposures_no_delete BEFORE DELETE ON portfolio_exposures BEGIN SELECT RAISE(ABORT, 'portfolio_exposures is append-only'); END;
        """
    )


def _add_performance_analytics_store(connection: sqlite3.Connection) -> None:
    """Add immutable analytics reports and performance checkpoints."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS analytics_reports (
            report_id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            analytics_version TEXT NOT NULL,
            scope_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            groups_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(report_type, analytics_version, source_fingerprint)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_reports_type_time
            ON analytics_reports(report_type, created_at);
        CREATE TABLE IF NOT EXISTS performance_snapshots (
            performance_snapshot_id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            portfolio_id TEXT,
            session_id TEXT,
            observed_at TEXT NOT NULL,
            equity REAL NOT NULL,
            drawdown REAL NOT NULL,
            pnl REAL NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (report_id) REFERENCES analytics_reports(report_id)
        );
        CREATE INDEX IF NOT EXISTS idx_performance_snapshots_report_time
            ON performance_snapshots(report_id, observed_at);
        CREATE TRIGGER IF NOT EXISTS analytics_reports_no_update
            BEFORE UPDATE ON analytics_reports BEGIN
            SELECT RAISE(ABORT, 'analytics_reports is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS analytics_reports_no_delete
            BEFORE DELETE ON analytics_reports BEGIN
            SELECT RAISE(ABORT, 'analytics_reports is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS performance_snapshots_no_update
            BEFORE UPDATE ON performance_snapshots BEGIN
            SELECT RAISE(ABORT, 'performance_snapshots is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS performance_snapshots_no_delete
            BEFORE DELETE ON performance_snapshots BEGIN
            SELECT RAISE(ABORT, 'performance_snapshots is append-only');
            END;
        """
    )


def _add_live_execution_store(connection: sqlite3.Connection) -> None:
    """Add append-only gateway orders, lifecycle events, and broker sync evidence."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS execution_orders (
            order_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            broker_order_id TEXT,
            client_order_key TEXT NOT NULL UNIQUE,
            signal_id TEXT,
            trade_id TEXT,
            portfolio_id TEXT,
            broker_name TEXT NOT NULL,
            execution_mode TEXT NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            expiry TEXT,
            strike REAL,
            option_type TEXT,
            order_type TEXT NOT NULL,
            product_type TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL,
            trigger_price REAL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (signal_id) REFERENCES research_signals(signal_id)
        );
        CREATE INDEX IF NOT EXISTS idx_execution_orders_signal ON execution_orders(signal_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_execution_orders_broker ON execution_orders(broker_name, created_at);
        CREATE TABLE IF NOT EXISTS order_events (
            event_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES execution_orders(order_id),
            UNIQUE(order_id, event_type, occurred_at)
        );
        CREATE INDEX IF NOT EXISTS idx_order_events_order_time
            ON order_events(order_id, occurred_at, event_id);
        CREATE TABLE IF NOT EXISTS broker_sync_events (
            sync_id TEXT PRIMARY KEY,
            broker_name TEXT NOT NULL,
            sync_type TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_broker_sync_events_broker_time
            ON broker_sync_events(broker_name, occurred_at);
        CREATE TRIGGER IF NOT EXISTS execution_orders_no_update
            BEFORE UPDATE ON execution_orders BEGIN
            SELECT RAISE(ABORT, 'execution_orders is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS execution_orders_no_delete
            BEFORE DELETE ON execution_orders BEGIN
            SELECT RAISE(ABORT, 'execution_orders is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS order_events_no_update
            BEFORE UPDATE ON order_events BEGIN
            SELECT RAISE(ABORT, 'order_events is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS order_events_no_delete
            BEFORE DELETE ON order_events BEGIN
            SELECT RAISE(ABORT, 'order_events is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS broker_sync_events_no_update
            BEFORE UPDATE ON broker_sync_events BEGIN
            SELECT RAISE(ABORT, 'broker_sync_events is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS broker_sync_events_no_delete
            BEFORE DELETE ON broker_sync_events BEGIN
            SELECT RAISE(ABORT, 'broker_sync_events is append-only');
            END;
        """
    )


def _add_multi_broker_asset_store(connection: sqlite3.Connection) -> None:
    """Add append-only broker, account, routing, provider, and instrument registry records."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS brokers (
            broker_id TEXT PRIMARY KEY,
            broker_name TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS instruments (
            instrument_id TEXT PRIMARY KEY,
            exchange TEXT NOT NULL,
            segment TEXT NOT NULL,
            symbol TEXT NOT NULL,
            trading_symbol TEXT NOT NULL,
            isin TEXT,
            expiry TEXT,
            strike REAL,
            option_type TEXT,
            lot_size INTEGER NOT NULL,
            tick_size REAL NOT NULL,
            currency TEXT NOT NULL,
            margin_group TEXT,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(exchange, segment, trading_symbol, expiry, strike, option_type)
        );
        CREATE INDEX IF NOT EXISTS idx_instruments_lookup
            ON instruments(exchange, segment, trading_symbol, status);
        CREATE TABLE IF NOT EXISTS broker_accounts (
            account_id TEXT PRIMARY KEY,
            broker_name TEXT NOT NULL,
            client_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            default_portfolio_id TEXT,
            status TEXT NOT NULL,
            permissions_json TEXT NOT NULL,
            execution_enabled INTEGER NOT NULL,
            last_sync_at TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(broker_name, client_id)
        );
        CREATE TABLE IF NOT EXISTS execution_routes (
            route_id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            broker_name TEXT NOT NULL,
            priority INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES broker_accounts(account_id),
            UNIQUE(portfolio_id, account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_execution_routes_portfolio
            ON execution_routes(portfolio_id, enabled, priority);
        CREATE TABLE IF NOT EXISTS market_providers (
            provider_id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL UNIQUE,
            asset_classes_json TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            priority INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS symbol_mappings (
            mapping_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            broker_name TEXT NOT NULL,
            broker_symbol TEXT NOT NULL,
            broker_token TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id),
            UNIQUE(instrument_id, broker_name),
            UNIQUE(broker_name, broker_symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_symbol_mappings_broker_symbol
            ON symbol_mappings(broker_name, broker_symbol);
        CREATE TRIGGER IF NOT EXISTS brokers_no_update BEFORE UPDATE ON brokers BEGIN SELECT RAISE(ABORT, 'brokers is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS brokers_no_delete BEFORE DELETE ON brokers BEGIN SELECT RAISE(ABORT, 'brokers is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS instruments_no_update BEFORE UPDATE ON instruments BEGIN SELECT RAISE(ABORT, 'instruments is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS instruments_no_delete BEFORE DELETE ON instruments BEGIN SELECT RAISE(ABORT, 'instruments is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS broker_accounts_no_update BEFORE UPDATE ON broker_accounts BEGIN SELECT RAISE(ABORT, 'broker_accounts is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS broker_accounts_no_delete BEFORE DELETE ON broker_accounts BEGIN SELECT RAISE(ABORT, 'broker_accounts is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS execution_routes_no_update BEFORE UPDATE ON execution_routes BEGIN SELECT RAISE(ABORT, 'execution_routes is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS execution_routes_no_delete BEFORE DELETE ON execution_routes BEGIN SELECT RAISE(ABORT, 'execution_routes is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS market_providers_no_update BEFORE UPDATE ON market_providers BEGIN SELECT RAISE(ABORT, 'market_providers is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS market_providers_no_delete BEFORE DELETE ON market_providers BEGIN SELECT RAISE(ABORT, 'market_providers is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS symbol_mappings_no_update BEFORE UPDATE ON symbol_mappings BEGIN SELECT RAISE(ABORT, 'symbol_mappings is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS symbol_mappings_no_delete BEFORE DELETE ON symbol_mappings BEGIN SELECT RAISE(ABORT, 'symbol_mappings is append-only'); END;
        """
    )


def _add_strategy_lab_store(connection: sqlite3.Connection) -> None:
    """Add append-only strategy, experiment, dataset, and notebook research records."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategies (
            strategy_id TEXT PRIMARY KEY,
            strategy_name TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            category TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            market TEXT NOT NULL,
            version TEXT NOT NULL,
            status TEXT NOT NULL,
            parent_strategy_id TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            UNIQUE(strategy_name, version)
        );
        CREATE TABLE IF NOT EXISTS strategy_configurations (
            configuration_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id),
            UNIQUE(strategy_id, checksum)
        );
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            market TEXT NOT NULL,
            source TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            snapshot_count INTEGER NOT NULL,
            checksum TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            experiment_name TEXT NOT NULL,
            objective TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            configuration_id TEXT NOT NULL,
            market TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            execution_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id),
            FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id),
            FOREIGN KEY(configuration_id) REFERENCES strategy_configurations(configuration_id),
            UNIQUE(strategy_id, experiment_name)
        );
        CREATE TABLE IF NOT EXISTS experiment_runs (
            run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            input_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            execution_time_ms REAL NOT NULL,
            results_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id),
            UNIQUE(experiment_id, input_fingerprint)
        );
        CREATE TABLE IF NOT EXISTS promotion_decisions (
            promotion_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            criteria_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            decision TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id),
            FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
        );
        CREATE TABLE IF NOT EXISTS research_notebook_entries (
            entry_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
        );
        CREATE INDEX IF NOT EXISTS idx_experiments_strategy ON experiments(strategy_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_experiment_runs_experiment ON experiment_runs(experiment_id, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_notebook_experiment ON research_notebook_entries(experiment_id, created_at);
        CREATE TRIGGER IF NOT EXISTS strategies_no_update BEFORE UPDATE ON strategies BEGIN SELECT RAISE(ABORT, 'strategies is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS strategies_no_delete BEFORE DELETE ON strategies BEGIN SELECT RAISE(ABORT, 'strategies is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS strategy_configurations_no_update BEFORE UPDATE ON strategy_configurations BEGIN SELECT RAISE(ABORT, 'strategy_configurations is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS strategy_configurations_no_delete BEFORE DELETE ON strategy_configurations BEGIN SELECT RAISE(ABORT, 'strategy_configurations is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS datasets_no_update BEFORE UPDATE ON datasets BEGIN SELECT RAISE(ABORT, 'datasets is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS datasets_no_delete BEFORE DELETE ON datasets BEGIN SELECT RAISE(ABORT, 'datasets is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS experiments_no_update BEFORE UPDATE ON experiments BEGIN SELECT RAISE(ABORT, 'experiments is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS experiments_no_delete BEFORE DELETE ON experiments BEGIN SELECT RAISE(ABORT, 'experiments is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS experiment_runs_no_update BEFORE UPDATE ON experiment_runs BEGIN SELECT RAISE(ABORT, 'experiment_runs is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS experiment_runs_no_delete BEFORE DELETE ON experiment_runs BEGIN SELECT RAISE(ABORT, 'experiment_runs is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS promotion_decisions_no_update BEFORE UPDATE ON promotion_decisions BEGIN SELECT RAISE(ABORT, 'promotion_decisions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS promotion_decisions_no_delete BEFORE DELETE ON promotion_decisions BEGIN SELECT RAISE(ABORT, 'promotion_decisions is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS research_notebook_entries_no_update BEFORE UPDATE ON research_notebook_entries BEGIN SELECT RAISE(ABORT, 'research_notebook_entries is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS research_notebook_entries_no_delete BEFORE DELETE ON research_notebook_entries BEGIN SELECT RAISE(ABORT, 'research_notebook_entries is append-only'); END;
        """
    )


def _add_enterprise_operations_store(connection: sqlite3.Connection) -> None:
    """Add append-only Enterprise Operations Center observations and governance."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS eoc_health_observations (
            health_id TEXT PRIMARY KEY, component TEXT NOT NULL, status TEXT NOT NULL,
            version TEXT NOT NULL, observed_at TEXT NOT NULL, uptime_seconds REAL,
            last_heartbeat_at TEXT, error_count INTEGER NOT NULL,
            average_processing_ms REAL, response_time_ms REAL, queue_backlog INTEGER,
            details_json TEXT NOT NULL, correlation_id TEXT, created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_health_component_time
            ON eoc_health_observations(component, observed_at);

        CREATE TABLE IF NOT EXISTS eoc_alerts (
            alert_id TEXT PRIMARY KEY, category TEXT NOT NULL, severity TEXT NOT NULL,
            component TEXT NOT NULL, message TEXT NOT NULL, deduplication_key TEXT NOT NULL UNIQUE,
            observed_at TEXT NOT NULL, correlation_id TEXT, details_json TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_alerts_severity_time
            ON eoc_alerts(severity, observed_at);

        CREATE TABLE IF NOT EXISTS eoc_audit_events (
            audit_id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
            entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
            before_json TEXT NOT NULL, after_json TEXT NOT NULL, correlation_id TEXT,
            created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_audit_entity_time
            ON eoc_audit_events(entity_type, entity_id, occurred_at);

        CREATE TABLE IF NOT EXISTS eoc_scheduler_observations (
            scheduler_event_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, status TEXT NOT NULL,
            observed_at TEXT NOT NULL, last_run_at TEXT, next_run_at TEXT, duration_ms REAL,
            result_json TEXT NOT NULL, correlation_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_scheduler_job_time
            ON eoc_scheduler_observations(job_id, observed_at);

        CREATE TABLE IF NOT EXISTS eoc_metrics (
            metric_id TEXT PRIMARY KEY, component TEXT NOT NULL, metric_name TEXT NOT NULL,
            value REAL NOT NULL, unit TEXT NOT NULL, observed_at TEXT NOT NULL,
            correlation_id TEXT, details_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_metrics_component_time
            ON eoc_metrics(component, metric_name, observed_at);

        CREATE TABLE IF NOT EXISTS eoc_notification_deliveries (
            delivery_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, channel TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT, attempted_at TEXT NOT NULL,
            details_json TEXT NOT NULL, FOREIGN KEY(alert_id) REFERENCES eoc_alerts(alert_id)
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_notifications_alert
            ON eoc_notification_deliveries(alert_id, attempted_at);

        CREATE TABLE IF NOT EXISTS eoc_configuration_history (
            configuration_event_id TEXT PRIMARY KEY, configuration_name TEXT NOT NULL,
            version TEXT NOT NULL, checksum TEXT NOT NULL, values_json TEXT NOT NULL,
            actor TEXT NOT NULL, occurred_at TEXT NOT NULL, correlation_id TEXT,
            created_by TEXT NOT NULL,
            UNIQUE(configuration_name, version, checksum)
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_configuration_name_time
            ON eoc_configuration_history(configuration_name, occurred_at);

        CREATE TABLE IF NOT EXISTS eoc_diagnostic_reports (
            diagnostic_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
            recommendation TEXT NOT NULL, details_json TEXT NOT NULL, observed_at TEXT NOT NULL,
            correlation_id TEXT, created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eoc_diagnostic_name_time
            ON eoc_diagnostic_reports(name, observed_at);
        """
    )
    immutable_tables = (
        "eoc_health_observations", "eoc_alerts", "eoc_audit_events",
        "eoc_scheduler_observations", "eoc_metrics", "eoc_notification_deliveries",
        "eoc_configuration_history", "eoc_diagnostic_reports",
    )
    for table in immutable_tables:
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )


def _add_research_knowledge_store(connection: sqlite3.Connection) -> None:
    """Add immutable deterministic knowledge facts and generated reports."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_facts (
            fact_id TEXT PRIMARY KEY,
            source_run_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            subject_key TEXT NOT NULL,
            strategy_id TEXT,
            experiment_id TEXT NOT NULL,
            market TEXT,
            metrics_json TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(source_run_id) REFERENCES experiment_runs(run_id),
            FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id),
            UNIQUE(source_run_id, domain, subject_type, subject_key)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_facts_domain_subject
            ON knowledge_facts(domain, subject_key, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_knowledge_facts_experiment
            ON knowledge_facts(experiment_id, occurred_at);
        CREATE TABLE IF NOT EXISTS knowledge_reports (
            report_id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            scope TEXT NOT NULL,
            scope_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            payload_json TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_reports_type_time
            ON knowledge_reports(report_type, generated_at);
        """
    )
    for table in ("knowledge_facts", "knowledge_reports"):
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )


def _add_portfolio_options_analytics_store(connection: sqlite3.Connection) -> None:
    """Add append-only deterministic portfolio/options analytic observations."""
    for table in (
        "portfolio_analytics", "position_analytics", "greeks_analytics",
        "option_chain_analytics", "iv_analytics", "stress_test_analytics",
        "strategy_analytics",
    ):
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (analysis_id TEXT PRIMARY KEY, "
            "subject_id TEXT NOT NULL, payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE, "
            "created_at TEXT NOT NULL)"
        )
        connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_subject_time ON {table}(subject_id, created_at)")
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )
        connection.execute(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
        )


def _add_market_intelligence_store(connection: sqlite3.Connection) -> None:
    """Add append-only Market Intelligence scanner observations."""
    for table in ("scanner_registry", "scanner_results", "scanner_rankings",
                  "sector_intelligence", "market_themes", "ranked_watchlists",
                  "scanner_alerts", "scanner_performance"):
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (record_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, "
            "payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)"
        )
        connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_subject_time ON {table}(subject_id, created_at)")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
                           f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
                           f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")


def _add_trade_journal_store(connection: sqlite3.Connection) -> None:
    """Add append-only trade-journal and deterministic learning observations."""
    for table in ("trade_journals", "trade_learning", "trade_performance",
                  "trade_compliance", "trade_timelines", "trade_statistics", "trade_reports"):
        connection.execute(f"CREATE TABLE IF NOT EXISTS {table} (record_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)")
        connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_subject_time ON {table}(subject_id, created_at)")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")


def _add_market_data_platform_store(connection: sqlite3.Connection) -> None:
    """Add authoritative append-only normalized market-data evidence."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS market_snapshot (
            snapshot_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            spot REAL NOT NULL,
            expiry TEXT NOT NULL,
            quality_state TEXT NOT NULL,
            latency_ms REAL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_market_data_snapshot_instrument_time
            ON market_snapshot(instrument_id, captured_at);
        CREATE TABLE IF NOT EXISTS provider_health (
            health_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            availability TEXT NOT NULL,
            latency_ms REAL,
            error_count INTEGER NOT NULL,
            heartbeat_at TEXT,
            circuit_state TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_provider_health_provider_time
            ON provider_health(provider, observed_at);
        CREATE TABLE IF NOT EXISTS provider_events (
            event_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_provider_events_provider_time
            ON provider_events(provider, occurred_at);
        CREATE TABLE IF NOT EXISTS source_transition (
            transition_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            from_provider TEXT,
            to_provider TEXT NOT NULL,
            reason TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_source_transition_instrument_time
            ON source_transition(instrument_id, occurred_at);
        """
    )
    for table in ("market_snapshot", "provider_health", "provider_events", "source_transition"):
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")


def _add_canonical_coa_store(connection: sqlite3.Connection) -> None:
    """Add append-only canonical-rule, evidence and replay audit records."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS coa_rule_registry (rule_id TEXT NOT NULL, version TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(rule_id, version));
        CREATE TABLE IF NOT EXISTS coa_versions (version_id TEXT PRIMARY KEY, engine_version TEXT NOT NULL, rule_manifest_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(engine_version));
        CREATE TABLE IF NOT EXISTS coa_evidence (evidence_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, rule_id TEXT NOT NULL, rule_version TEXT NOT NULL, result TEXT NOT NULL, weight REAL NOT NULL, comment TEXT NOT NULL, occurred_at TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_coa_evidence_snapshot ON coa_evidence(snapshot_id, occurred_at);
        CREATE TABLE IF NOT EXISTS compatibility_matrix (matrix_id TEXT PRIMARY KEY, structural_direction TEXT NOT NULL, tactical_action TEXT NOT NULL, decision TEXT NOT NULL, version TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(structural_direction, tactical_action, version));
        CREATE TABLE IF NOT EXISTS coa_replay (replay_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, canonical_version TEXT NOT NULL, matches_legacy INTEGER NOT NULL, differences_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(snapshot_id, canonical_version));
        CREATE TABLE IF NOT EXISTS rule_changes (change_id TEXT PRIMARY KEY, rule_id TEXT NOT NULL, from_version TEXT, to_version TEXT NOT NULL, change_note TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    for table in ("coa_rule_registry", "coa_versions", "coa_evidence", "compatibility_matrix", "coa_replay", "rule_changes"):
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")

def _add_trade_decision_store(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS trade_decision (decision_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, action TEXT NOT NULL, status TEXT NOT NULL, confidence REAL NOT NULL, valid_until TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decision_evidence (evidence_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, category TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(decision_id) REFERENCES trade_decision(decision_id));
        CREATE TABLE IF NOT EXISTS decision_lifecycle (event_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL, occurred_at TEXT NOT NULL, payload_json TEXT NOT NULL, FOREIGN KEY(decision_id) REFERENCES trade_decision(decision_id));
        CREATE TABLE IF NOT EXISTS decision_rejection (rejection_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, rule_id TEXT NOT NULL, severity TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(decision_id) REFERENCES trade_decision(decision_id));
        CREATE TABLE IF NOT EXISTS decision_versions (version_id TEXT PRIMARY KEY, version TEXT NOT NULL UNIQUE, manifest_json TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    for table in ("trade_decision", "decision_evidence", "decision_lifecycle", "decision_rejection", "decision_versions"):
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END")

RESEARCH_MIGRATIONS = (
    Migration(version=1, name="research_schema_v1", apply=_create_research_schema),
    Migration(version=2, name="market_snapshot_capture_v2", apply=_add_market_capture_fields),
    Migration(version=3, name="coa_research_results_v3", apply=_add_coa_result_store),
    Migration(version=4, name="validation_evidence_v4", apply=_add_validation_result_store),
    Migration(version=5, name="research_signals_v5", apply=_add_research_signal_store),
    Migration(version=6, name="event_sourced_paper_trades_v6", apply=_add_paper_execution_store),
    Migration(version=7, name="portfolio_risk_v7", apply=_add_portfolio_risk_store),
    Migration(version=8, name="performance_analytics_v8", apply=_add_performance_analytics_store),
    Migration(version=9, name="live_execution_gateway_v9", apply=_add_live_execution_store),
    Migration(version=10, name="multi_broker_asset_v10", apply=_add_multi_broker_asset_store),
    Migration(version=11, name="strategy_lab_v11", apply=_add_strategy_lab_store),
    Migration(12, "enterprise_operations_center", _add_enterprise_operations_store),
    Migration(13, "research_knowledge_engine", _add_research_knowledge_store),
    Migration(14, "advanced_portfolio_options_analytics", _add_portfolio_options_analytics_store),
    Migration(15, "market_intelligence_scanner", _add_market_intelligence_store),
    Migration(16, "trade_journal_learning", _add_trade_journal_store),
    Migration(17, "market_data_platform", _add_market_data_platform_store),
    Migration(18, "canonical_coa_engine", _add_canonical_coa_store),
    Migration(19, "trade_decision_engine", _add_trade_decision_store),
)
