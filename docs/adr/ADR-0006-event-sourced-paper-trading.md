# ADR-0006: Event-Sourced Paper Trading

- **Status:** Accepted
- **Date:** 2026-07-19

## Decision

Paper-trade identities and all lifecycle changes are stored separately as
append-only events. Current state is produced by a deterministic projector.

## Rationale

An event stream preserves the exact sequence of fills, targets, stop moves,
costs, and exits needed for replay and research. It avoids destructive trade
updates and supports auditable reconstruction.

## Execution policy

Fill policy, price source, slippage, transaction costs, partial allocation,
trailing mode, ambiguity policy, and session-end behavior are configuration
values. The default ambiguity handling is conservative to avoid overstated
results.

## Separation from live execution

This subsystem consumes stored research signals and snapshots only. It has no
broker imports, authentication, order routing, capital deployment, or portfolio
risk controls. Those require separate future decisions.
