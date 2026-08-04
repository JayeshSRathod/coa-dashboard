# ADR-0018 — Combined COA Scenario Shadow Capture

## Decision

CQRP records the established COA1 structural scenarios 1–9 and the frozen COA2
tactical scenarios as combined IDs 10–18 in a separate append-only scenario
track table.

## Rationale

This starts collecting the full combined scenario evidence immediately while
preserving baseline COA results and avoiding an unvalidated replacement model.

## Consequences

The scenario track is observational. Any future trading-rule change requires a
separate versioned ADR, replay comparison, evidence review, and PAPER-only
validation.

Native COA2 value `0` remains explicitly unclassified. It must never be
converted into structural Scenario 9 merely to fit an analytics bucket.
