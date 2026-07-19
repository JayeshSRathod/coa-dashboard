# Sprint-008: Portfolio Risk and Capital Management Engine

## Objective

Add a deterministic, auditable risk layer between persisted research signals and the future paper execution subsystem.

## Delivered

- Schema migration v7 for portfolios, risk decisions, capital events, and exposure checkpoints.
- Append-only repository abstractions for each portfolio-risk aggregate.
- Versioned configuration supporting fixed quantity, capital, risk, percentage portfolio, and a future volatility sizing mode.
- Deterministic limits for capital reserve, per-trade and portfolio risk, daily loss, drawdown, positions, instrument, expiry, and option-type exposure.
- Risk pipeline that stores decisions and reserves capital only for approved/reduced paper candidates.
- Structured events and deterministic/idempotent decision handling.
- ADR-0007 and regression tests.

## Explicit exclusions

Frozen COA mathematics, dashboard behavior, broker authentication, legacy ledger, live execution, and trade creation remain unchanged.
