# Sprint 036 — Evidence-gated research capture enrichment

## Objective

Make the one-month COA study auditable without changing frozen COA mathematics,
validation thresholds, signal logic, or paper-execution behaviour.

## Captured evidence

- Explicit FYERS source symbol per snapshot for NIFTY, BANKNIFTY and FINNIFTY.
- Provider-reported expiry where present, requested expiry, days-to-expiry and
  an immutable capture-profile record.
- Returned strike-window bounds and count. CQRP records every provider-returned
  contract; it does not use this metadata to discover or rank a trade strike.
- Bid/ask quantity only where FYERS supplies it, alongside existing bid, ask,
  volume, OI and OI change fields.

## Evidence gate

These fields are observational. They must not become validation inputs until
`EXP-0001-market-data-confirmation-study.md` has met its availability,
comparable-outcome and out-of-sample criteria. Missing fields remain missing;
CQRP must not estimate depth, IV, Greeks, or an expiry.

## Study window

Use the existing raw option-chain snapshots to derive five, ten and thirty
minute changes during analysis. This preserves replayability and avoids storing
a decision-dependent derived feature as if it were market truth.
