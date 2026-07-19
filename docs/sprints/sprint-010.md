# Sprint-010: Live Execution Gateway & Order Management

## Objective

Add a broker-agnostic, safety-first gateway without changing research, validation, signals, portfolio risk, or the existing deterministic paper-trading engine.

## Delivered

- Migration v9: immutable execution orders, lifecycle events, and broker synchronization evidence.
- Configuration-driven PAPER, LIVE, SIMULATION, and DISABLED modes; default configuration is DISABLED.
- Safety gate for approval references, instrument fields, order limits, trading hours, kill switch, emergency stop, dry-run, and live enablement.
- Event-sourced order lifecycle and pure lifecycle projector.
- Fyers adapter using injected credentials and the existing Fyers authentication utility; Dhan and Zerodha contract adapters.
- Controlled retries for network failures, read-only broker synchronization, structured logging, and regression tests.

## Safety guarantee

Only LIVE mode can invoke a broker adapter. LIVE requires explicit configuration: trading_enabled true, kill_switch false, emergency_stop false, dry_run false, and in-hours submission. Sprint tests use no credentials and make no network order calls.
