# Sprint 034 — Combined Scenario Capture & Pre-Close Orchestration

## Scope

Sprint 034 records the already-defined combined COA scenario catalog as
append-only research evidence. Structural COA1 remains scenarios 1–9. Frozen
COA2 tactical states keep their native IDs 1–9 and are stored as combined IDs
10–18. Native COA2 value `0` is stored as `0 / unclassified`, never forced
into one of the 18 defined scenarios. This is an observation track, not a new
trading formula.

## Runtime behavior

- Each successfully captured snapshot receives one immutable combined scenario
  record.
- Existing dynamic-structure events continue to contain both COA1 and COA2
  values; the new repository provides a direct per-snapshot replay read model.
- Next-session plans are created only from snapshots captured between 15:00 and
  15:20 Asia/Kolkata time.
- The first valid next-session snapshot continues to revalidate a prior plan.
- `scripts/run_maturity_research_batch.py` replays missing combined-scenario
  and dynamic-structure evidence from stored snapshots after the worker stops.
  It has no FYERS request or broker capability.

## Safety

The work does not alter `engine/coa_math.py`, signal rules, validation scores,
risk limits, broker behavior, or paper execution. All new records are
append-only and remain PAPER/research evidence.
