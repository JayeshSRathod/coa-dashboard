# ADR-0015: Market Intelligence Engine

- Status: Accepted
- Date: 2026-07-19

Scanner rules are independent components registered in a deterministic registry.
Ranking uses fixed configured weights. Sector breadth and theme labels arise from
explicit thresholds only. Watchlists and alert observations are append-only,
deduplicated by input fingerprints, and never carry execution authority.
