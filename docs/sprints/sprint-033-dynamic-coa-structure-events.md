# Sprint 033 — Dynamic COA Structure & Scenario Events

## Purpose

Create a deterministic, replayable evidence layer around the frozen COA
calculation. It records how CE/PE volume and OI walls, COA levels, spot, and
paper-research decisions evolve over time.

## Recorded evidence

- Top CE/PE walls by volume and OI at each captured strike.
- Contract-level expiry context for every wall and trigger, e.g. `NIFTY 24000
  CE expiry 2026-07-28`; a feed-level expiry is used when a contract row does
  not expose a separate expiry.
- Wall migration, volume burst, OI build and volume-first/OI-later confirmation.
- Support/resistance/EOS/EOR interactions, resistance breaks, false breaks,
  EOS rejection/break, five-minute confirmation, pullback/retest and
  continuation re-entry evidence.
- Feed degradation and capture gaps.
- Spot distance from Support, Resistance, EOS and EOR at every structure
  snapshot, plus one immutable five-minute `CONFIRMED` or `FAILED` outcome for
  each breakout, rejection, retest or continuation/re-entry event.
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

## Dashboard scope

All market-facing Dashboard 2.0 pages use one shared instrument selector
(`NIFTY`, `BANKNIFTY`, or `FINNIFTY`). COA Research adds session and event-type
filters, while **Strike Activity** exposes the top CE/PE Volume and OI wall
records with their actual strike, side, rank, metric value, timestamp and
snapshot ID. COA Research and Strike Activity export the complete selected
session (up to the guarded 25,000-record limit), not merely the latest 50
events. Every tabular read model provides CSV and JSON export. This is a
read-only presentation change; it does not create a signal or place an order.
