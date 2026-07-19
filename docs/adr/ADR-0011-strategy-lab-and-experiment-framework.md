# ADR-0011: Strategy Lab and Experiment Framework

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-012

## Decision

CQRP will manage strategies, configurations, datasets, experiments, run results, promotion evidence, and research notes as append-only records. A strategy version and its configurations are immutable after registration. Clones receive new identity and their own copied configuration snapshots, never shared mutable settings.

## Reproducibility

Each dataset has a checksum; each configuration has a checksum; an experiment run fingerprint combines strategy, dataset, configuration, and execution mode. A matching successful run is returned instead of rerun.

## Promotion workflow

Promotion evaluation generates a recommendation from configured metrics but only records evidence. It cannot promote, deploy, or modify a strategy automatically.

## Consequences

The existing replay and analysis pipeline remains independently owned. The Strategy Lab injects it through a runner contract, avoiding copies of strategy, risk, paper-execution, or analytics logic.
