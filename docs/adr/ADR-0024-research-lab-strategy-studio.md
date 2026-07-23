# ADR-0024: Research Lab & Strategy Studio

## Decision

Extend the existing append-only `src.strategy_lab` strategy registry, experiment manager, dataset registry, and manual promotion evidence with pure research utilities in `src.research`.

## Rationale

This avoids a second competing strategy database.  Backtesting, optimization, walk-forward validation, Monte Carlo robustness, performance metrics, and lifecycle checks remain deterministic and receive the CQRP pipeline as an injected dependency.  They do not duplicate or modify COA mathematics, risk policy, paper execution, or OMS behavior.

## Consequences

Research output is reproducible from immutable input data and declared parameters.  A promotion may be evaluated automatically, but approval and transition to production require an identified human approver.
