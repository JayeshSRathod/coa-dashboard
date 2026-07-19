# ADR-0007: Portfolio Risk and Capital Management Engine

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-008

## Context

CQRP paper execution requires a reproducible pre-trade control without changing frozen COA mathematics or creating any live-order path.

## Decision

Introduce a deterministic, configuration-driven portfolio risk layer. It consumes persisted research signals and portfolio state, produces append-only risk decisions, and records capital reservations and exposure checkpoints through repository abstractions.

Risk decisions are idempotent for the tuple `signal_id, portfolio_id, risk_version, experiment_id`. The allowed outcomes are `APPROVED`, `REJECTED`, and `REDUCED_SIZE`. `QUEUED` remains reserved for a future scheduling policy.

## Consequences

- Portfolio capital and exposure are replayable from immutable records.
- Risk is separated from COA, broker, dashboard, and live-execution concerns.
- New risk configurations require a version change, preserving historical interpretation.
- Position sizing is deterministic; volatility sizing remains an explicit future framework until volatility inputs are part of the versioned signal contract.
