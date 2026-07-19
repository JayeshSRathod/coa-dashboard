# Sprint-004 — COA Research Engine Integration

## Objective

Integrate the frozen COA v1 structural engine with persisted snapshots and replay
without altering COA mathematics, the Streamlit dashboard, broker code, or the
legacy ledger.

## Flow

SnapshotRepository → COAResearchPipeline → FrozenCOAAdapter → frozen engine → COAResultRepository

A live capture can invoke the pipeline automatically by passing
pipeline.process_snapshot_id as the optional SnapshotCaptureService after_store
callback. Capture remains durable if analysis fails; the failure is logged as an
immutable system event and can be replayed safely.

## Storage

Migration 3 adds append-only coa_results, linked to market_snapshots.
The uniqueness key (snapshot_id, engine_version, experiment_key) prevents
unintended duplicate analysis while allowing the same snapshot to be evaluated
by a future engine version or a separately named experiment.

## Explicit limitations

- Momentum and diversion are None in this sprint because the frozen structural
  engine does not produce them from one snapshot.
- No trade signal, validation score, paper-trade action, or dashboard change is
  introduced.
- Processing duration and result UUID are observability metadata, not inputs to
  deterministic analysis.
