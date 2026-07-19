# Sprint-012: Strategy Lab & Experiment Framework

## Objective

Provide a reproducible, research-only R&D environment for strategy versions, configurations, datasets, historical experiments, comparisons, and manual promotion recommendations.

## Delivered

- Migration v11: append-only strategy, configuration, dataset, experiment, run, promotion, and notebook records.
- Immutable strategy version registry with configuration-inheriting clones.
- Dataset checksums and deterministic experiment input fingerprints.
- Experiment runner contract that invokes an injected full CQRP pipeline and records immutable results.
- Experiment comparison, promotion-criteria evaluation, automatic notebook evidence, configuration, structured logging, and tests.

## Safety

Promotion is evidence-based but manual. The runner does not alter any production strategy, execution mode, broker, or live order path.
