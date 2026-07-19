# Sprint-014: Enterprise Operations Center

## Objective
Add a centralized, append-only operational observability layer for CQRP without
changing any deterministic research, validation, signal, risk, execution, or
analytics behavior.

## Delivered
- Immutable health, alert, audit, scheduler, metric, notification,
  configuration-governance, and diagnostics records (migration v12).
- Health aggregation across components, alert deduplication, scheduler status,
  audit search, chronological activity timeline, configuration history, and
  injected read-only diagnostics.
- Notification router with external notifications disabled by default.
- Dashboard service APIs: health, alerts, timeline, scheduler, audit,
  configuration history, and diagnostics.

## Safety boundary
The EOC owns only its operational event tables. It has no imports from, and no
write paths to, the frozen COA engine, signals, risk, live execution, paper
trades, or analytics. Diagnostics are injected probes and exceptions are
recorded rather than propagated.
