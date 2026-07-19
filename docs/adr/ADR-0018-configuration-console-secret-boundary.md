# ADR-0018: Configuration Console Secret Boundary

## Decision

Use a dedicated configuration service and secret-store abstraction. Environment variables and Streamlit secrets are read-only deployment sources; the local OS credential manager is the only supported save target for raw credentials.

## Consequences

Configuration history is sanitized and versioned outside the repository. CQRP stores no raw broker PIN, token, secret, or Telegram credential in SQLite, logs, source files, or Git. The dashboard permits only `DISABLED` and `PAPER` execution modes.
