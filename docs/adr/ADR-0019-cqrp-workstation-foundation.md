# ADR-0019 — CQRP 3.0 workstation foundation

CQRP will retain Streamlit Dashboard 2.0 for configuration, diagnostics, and rapid internal views. Its primary decision interface will move incrementally to a local React and TypeScript workstation under `workstation/`.

The first CQRP 3.0 delivery provides role-based workspace layouts and static, serializable view contracts only. It neither calls brokers nor implements trading, risk, scanner, COA, Greeks, or persistence logic. Future work must consume versioned read-only APIs owned by CQRP application services.

This preserves the deterministic backend while enabling responsive panel-based workflows, keyboard navigation, and later multi-monitor layouts.
