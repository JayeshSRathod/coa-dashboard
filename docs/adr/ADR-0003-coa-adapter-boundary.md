# ADR-0003: COA Adapter Boundary

- **Status:** Accepted
- **Date:** 2026-07-19

## Decision

CQRP accesses frozen COA v1 only through FrozenCOAAdapter, which implements
the stable AnalysisEngine contract.

## Rationale

The legacy COA engine accepts a pandas option-chain frame, spot, and strike
step. CQRP stores provider-neutral snapshot records. The adapter performs only
this input/output translation and invokes the existing function unchanged; it
does not reimplement or reinterpret COA formulas.

## Dependency direction

research pipeline → analysis contract → adapter → engine/coa_math.py

Repositories and replay services must not call the frozen engine. The dashboard
must not call the adapter directly.

## Versioning and determinism

Each result records the immutable engine version. The same snapshot and engine
version must have identical analytical values. UUID, creation time, and measured
duration are persistence/observability metadata and may differ before
idempotent storage resolves to the first saved result.

## Consequences

Future COA versions or experimental engines implement the same contract. The
database uniqueness key prevents accidental duplicate processing of a snapshot
by the same engine and experiment. Changes to the frozen engine require a
separate ADR and review.
