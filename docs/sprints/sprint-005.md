# Sprint-005 — Validation Engine and Confidence Scoring

## Objective

Create deterministic, configuration-driven evidence assessment from persisted
market snapshots and COA research results. Validation does not create a trade
signal, alter COA mathematics, or execute an order.

## Components and default weights

| Component | Weight |
| --- | ---: |
| Volume | 20% |
| Open interest | 25% |
| Strike quality | 15% |
| Liquidity | 20% |
| Market context | 20% |

Weights and the minimum research-valid score are owned by ValidationConfig.
Historical-performance evidence is represented explicitly as null in this sprint;
no parameter optimisation or trade filter is inferred from unavailable data.

## Persistence

Migration 4 adds append-only validation_results. The uniqueness key
(coa_result_id, validation_version, experiment_key) prevents duplicate
processing while allowing future validation revisions and experiments.

## Replay and incomplete data

ValidationResearchPipeline processes individual COA results or an ordered session
replay. A failure is logged as an immutable system event and does not halt the
remaining session. Missing evidence yields an explicit component failure or
warning; it is never fabricated.
