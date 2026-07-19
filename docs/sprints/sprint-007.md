# Sprint-007 — Event-Sourced Paper Trading Engine

## Objective

Add deterministic paper execution for eligible research signals only. The engine
has no broker client, authentication path, live order capability, or dashboard
trading control.

## Lifecycle

Trade identities are immutable. Every change is appended as a lifecycle event;
the projector reconstructs current state, quantity remaining, P&L, MAE/MFE,
levels, and exit reason. Entries use configured fill policy and quotes. The
default is NEXT_SNAPSHOT with conservative option pricing assumptions.

## Conservative simulation

Same-snapshot stop/target conflicts are resolved by the configured ambiguity
policy, defaulting to CONSERVATIVE. Slippage and costs are configurable from the
first release. Target 1 can allocate a partial exit; the default trailing mode
moves the structural stop to breakeven after that exit.

## Boundary

This sprint is trade-level simulation only. Portfolio risk, capital allocation,
live execution, and adaptive optimisation remain out of scope.
