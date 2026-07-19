# ADR-0012: Deterministic Research Knowledge Engine

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-013

## Decision
CQRP will materialize completed experiment evidence into append-only
knowledge facts. Facts are grouped by strategy, experiment, scenario,
instrument, market, validation, and portfolio domains.

## Determinism
The extractor derives facts only from an immutable completed experiment run and
its immutable experiment/strategy metadata. Idempotency is guaranteed by the
source run and fact identity. Query rankings use explicit numeric aggregation
and stable lexical tie-breaking. Reports use a content fingerprint.

## Integration
The Strategy Lab accepts an optional knowledge builder. Its default is None,
which preserves all existing behavior. When supplied, only completed runs are
observed and facts are appended; research, risk, signals, execution, and
analytics are never changed.

## Future extension
AI may later consume the immutable facts through a separate advisory layer. It
must not replace the deterministic extractor, queries, reports, or repositories.
