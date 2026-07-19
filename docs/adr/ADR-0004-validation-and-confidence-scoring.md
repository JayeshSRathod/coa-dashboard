# ADR-0004: Validation and Confidence Scoring

- **Status:** Accepted
- **Date:** 2026-07-19

## Decision

Validation is a separate deterministic evidence layer between persisted COA
research results and any future signal engine.

## Rationale

COA describes structure; it is not replaced or reinterpreted by validation.
Volume, OI, strike quality, liquidity, and market context are recorded as
research evidence and weighted into a confidence classification. The
classification is not a trade instruction.

## Configuration and determinism

Weights live in ValidationConfig and must sum to one. Given the same snapshot,
COA result, configuration, and validation version, component and overall scores
are identical. IDs, timestamps, and processing duration are metadata only.

## Incomplete data and history

Unavailable input produces an explicit warning or failure. Historical evidence
has a nullable field and placeholder status until a later research sprint
provides adequate data; Sprint-005 does not optimise weights or invent history.

## Consequences

The persistence layer records immutable results keyed by COA result, validation
version, and experiment. Repositories and dashboards do not contain validation
SQL or component calculations. Future signal logic may consume this evidence
only through a separate approved sprint.
