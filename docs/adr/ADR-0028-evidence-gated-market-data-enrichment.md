# ADR-0028: Evidence-Gated Market-Data Enrichment

## Context

CQRP can capture or potentially request additional market fields such as
bid/ask quantities, quote velocity and provider Greeks. These fields increase
data volume, provider dependency and system complexity. A field being available
does not establish that it improves COA outcomes.

## Decision

Additional market data will enter CQRP through a three-phase, evidence-gated
process:

1. Verify provider payload, coverage, freshness and instrument mappings.
2. Capture it alongside the frozen baseline as append-only shadow evidence.
3. Promote it only after pre-registered, chronological paper-trading analysis
   shows an incremental and robust benefit.

The authoritative study design is
[`EXP-0001`](../research/EXP-0001-market-data-confirmation-study.md).

## Consequences

- No depth, quote velocity, independently calculated Greek or multi-index
  feature is added merely for display.
- Bid/ask spread may improve execution realism without becoming a directional
  signal.
- Provider Greeks remain contextual until their quality is demonstrated.
- Every future promotion requires an explicit configuration/strategy version,
  deterministic tests and human approval.
- Frozen COA calculations and current paper-only execution remain unchanged.
