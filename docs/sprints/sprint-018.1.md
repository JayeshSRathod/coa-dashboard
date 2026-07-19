# Sprint-018.1 — Configuration Console & Broker Credential Management

## Scope

Adds a secure local Configuration page for Dhan, Fyers, Telegram, execution safety, scanner/risk settings, sanitized configuration history, and safe connection-readiness checks.

## Security boundary

- Raw credentials are read from environment variables/Streamlit secrets or saved locally through the operating-system credential manager.
- Local configuration JSON contains only non-secret settings, presence flags, audit metadata, and fingerprints.
- Raw credentials are never rendered, logged, written to SQLite, or committed to Git.
- Network broker tests and live execution are intentionally unavailable.

## Execution safety

The only accepted modes are `DISABLED` and `PAPER`. Every saved execution configuration forces `trading_enabled=false`, `dry_run=true`, and `kill_switch=true`.
