# CQRP Research Schema v1

The research schema is separate from the v1 `intraday_ledger` database.

| Table | Purpose |
| --- | --- |
| `schema_migrations` | Applied migration history |
| `strategy_profiles` | Versioned strategy DNA and configuration |
| `market_snapshots` | One immutable market/COA observation per poll |
| `signals` | A generated recommendation derived from a snapshot |
| `signal_validations` | Individual gate results for a signal |
| `paper_trades` | Paper trade opened from a signal |
| `trade_updates` | Append-only trade-management observations |
| `trade_exits` | Final exit event and measured outcome |
| `system_events` | API, scheduler, health, and data-quality events |

All event timestamps are UTC ISO-8601 strings. JSON columns retain explanatory context and raw payloads so a later replay engine can reconstruct decisions without recalculating historical market state.