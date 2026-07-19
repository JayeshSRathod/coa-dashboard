# Sprint-001 — Platform Foundation

## Goal

Establish CQRP v2 engineering boundaries without modifying existing COA mathematics, dashboard behaviour, broker integrations, or ledger behaviour.

## Deliverables

- CQRP documentation and ADR structure
- configuration, version, and logging utilities
- SQLite connection, repository, and migration boundaries
- contributor and GitHub templates
- empty tracked runtime directories

## Acceptance criteria

1. Existing `app.py`, `engine/`, and `db/ledger.py` are unchanged.
2. New infrastructure uses only the Python standard library.
3. Logging creates runtime directories on demand.
4. SQLite access is available through `src.persistence`, not the dashboard.
5. Foundation modules can be imported with Python's standard test runner.

## Explicitly out of scope

Research tables, snapshot capture, validation scores, paper execution, analytics, replay, and strategy-rule changes.