# Sprint 301 — CQRP Decision Workstation Shell

## Delivered

- Feature-flagged `CQRP_WORKSTATION_ENABLED` application shell.
- Fixed Streamlit sidebar navigation, selected instrument, operational rail, and optional Dark/Light theme selector.
- All legacy Dashboard 2.0 pages remain the fallback when the flag is off.

## Safety

The shell opens read-only service views. It does not fetch a second market-data stream, write to SQLite, or call a broker order endpoint.
