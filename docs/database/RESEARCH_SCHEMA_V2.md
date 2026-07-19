# CQRP Research Schema v2 — Market Capture

Migration 2 extends `market_snapshots` with capture/replay metadata:

- `session_id`
- `market_captured_at` and `ingested_at`
- futures, ATM, and expiry metadata
- `data_completeness`, `is_complete`, and missing-strike JSON
- provider metadata JSON

The immutable snapshot record continues to retain the normalized option chain and the COA payload as JSON. Indexes support instrument/time, session/time, and chronological replay reads.