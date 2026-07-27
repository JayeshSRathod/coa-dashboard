# Sprint 033 — Dynamic COA Structure & Scenario Events

## Purpose

Create a deterministic, replayable evidence layer around the frozen COA
calculation. It records how CE/PE volume and OI walls, COA levels, spot, and
paper-research decisions evolve over time.

## Recorded evidence

- Top CE/PE walls by volume and OI at each captured strike.
- Wall migration, volume burst, OI build and volume-first/OI-later confirmation.
- Support/resistance/EOS/EOR interactions, resistance breaks, false breaks,
  EOS rejection/break, five-minute confirmation, pullback/retest and
  continuation re-entry evidence.
- Feed degradation and capture gaps.
- Linked COA scenario track, validation result, research signal, risk decision,
  paper candidate/trade and outcome state where they exist.

## Scenario contract

The event schema records structural COA1 scenarios as IDs 1–9 and uses the
combined IDs 10–18 for tactical COA2 scenarios. The existing frozen COA2
classifier reads consecutive total Call/Put OI changes from persisted snapshots;
its native tactical ID (1–9) is retained in each event payload. No scenario is
auto-enabled for trading by this work.

## Safety

This is an observation and replay layer. It does not modify `engine/coa_math.py`,
signal rules, validation thresholds, risk limits, paper execution rules or
broker/live execution. Every persisted wall/event is append-only.
