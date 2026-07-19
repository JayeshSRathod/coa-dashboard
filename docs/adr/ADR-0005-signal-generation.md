# ADR-0005: Deterministic Signal Generation

- **Status:** Accepted
- **Date:** 2026-07-19

## Decision

CQRP introduces a standalone signal domain after validation and before any
future execution domain. SignalEngine produces research recommendations only.

## Rationale

Separating signals from execution makes every candidate replayable,
explainable, and safe to analyse without broker access. Signal thresholds and
scenario mappings are configuration-owned, not embedded in orchestration code.

## Determinism and replay

Given the same snapshot, COA result, validation result, configuration, and
signal version, the signal type, direction, levels, confidence, reasons, and
warnings are identical. UUIDs, timestamps, and timings are metadata only.

## Explainability and safety

BUY, SELL, WATCHLIST, and NO_SIGNAL all persist a reason trail. A signal cannot
place or modify an order. Stop and trailing fields remain null in this sprint
because risk and trade lifecycle management are future concerns.

## Consequences

research_signals is append-only and uniquely keyed to prevent duplicate
processing. Repositories contain persistence only; the dashboard and broker
modules do not call signal rules directly.
