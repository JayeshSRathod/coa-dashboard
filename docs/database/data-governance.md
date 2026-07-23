# CQRP Data Governance

CQRP's research database is an append-only audit store. Snapshots, COA results, validation results, signals, trade events, risk decisions, analytics, and operational records are linked by immutable identifiers.

## Rules

- Access persistence through `src/persistence` repositories; UI and engines do not execute direct SQL.
- Add database changes as ordered migrations and document them in the relevant sprint record.
- Preserve historical records. Corrections are represented as new events or superseding records, never updates to research evidence.
- Do not store credentials, PINs, refresh tokens, or API secrets in SQLite.
- Back up local research databases before schema changes and before paper-trading sessions.

See [schema v1](RESEARCH_SCHEMA_V1.md) and [schema v2](RESEARCH_SCHEMA_V2.md) for the original database foundation.
