# Sprint 032 — Manual Observation Notes

## Purpose

Capture the operator's end-of-session COA observations as immutable research
evidence. This closes the gap between recorded snapshots and observations such
as dynamic wall migration, EOS/EOR reactions, volume bursts, delayed OI
confirmation, momentum stalls, and re-entry conditions.

## Scope

- Append-only `manual_observations` migration and repository.
- Dashboard **Observation Notes** page linked to the existing CQRP research
  database through the repository layer.
- Structured event types, optional COA scenario (1–18), price levels, expected
  and actual outcomes, and a free-text evidence narrative.
- Deterministic tests for validation, persistence, retrieval, and immutability.

## Safety boundary

An observation is `MANUAL` evidence only. It cannot modify frozen COA
mathematics, validation scores, signal generation, risk decisions, paper-trade
events, broker configuration, or execution mode. Corrections must be recorded
as a new observation rather than editing a previous entry.

## Operating procedure

After market close, open **Observation Notes**, select the session date and
instrument, record the event and relevant levels, then describe the expected
and actual result. Use `CAPTURE_GAP` when the worker missed a period so the
weekly review does not mistake absent evidence for a failed COA level.
