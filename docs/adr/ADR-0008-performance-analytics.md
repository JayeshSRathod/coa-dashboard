# ADR-0008: Performance Analytics and Backtesting Engine

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-009

## Context

CQRP needs reproducible evidence about completed paper-trade performance while preserving all upstream decisions and event-sourced execution records.

## Decision

Use a pure analytics engine over reconstructed closed trade states. A repository-backed service supplies immutable trade identities and events, then persists immutable report artifacts and performance snapshots. Reports are identified by a deterministic fingerprint of ordered source trades, scope, and analytics version.

## Metric conventions

Profit factor is null when there are no losses. Sharpe and Sortino use trade-level normalized returns and are research metrics, not annualized investment advice. Calmar and recovery factor use net profit divided by maximum drawdown. Omega is reserved as an explicit future framework.

## Consequences

- Analytics cannot create, modify, or execute trades.
- Reports are reproducible, exportable, and versioned.
- SQLite indexes support ordered historical reads; future cache implementations must use the source fingerprint and never overwrite a report.
