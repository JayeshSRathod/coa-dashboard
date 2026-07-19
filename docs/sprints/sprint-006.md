# Sprint-006 — Deterministic Signal Generation Engine

## Objective

Convert persisted COA and validation evidence into immutable research signal
recommendations. Signals are not orders and this sprint has no paper-trading,
broker, position, stop-management, or live-execution behavior.

## Rules and explainability

SignalConfig owns thresholds and scenario-to-direction mapping. The engine
creates BUY or SELL only when a configured scenario and all required validation
thresholds pass. An enabled scenario with incomplete evidence becomes WATCHLIST;
an unconfigured scenario becomes NO_SIGNAL. Every outcome persists its reasons
and warnings for replay.

## Candidate levels

BUY candidates expose the existing structural EOS as entry and EOR as second
reference target. SELL candidates invert those references. The midpoint is a
research target reference. Stop loss and trailing reference stay null because
risk and execution management are explicitly deferred to later sprints.

## Persistence and replay

Migration 5 adds append-only research_signals keyed by validation, signal
version, and experiment. SignalResearchPipeline replays validation results in
session order, and identical inputs plus configuration yield identical
decision values.
