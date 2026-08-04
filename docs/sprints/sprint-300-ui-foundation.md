# Sprint 300 — Decision Workstation UI Foundation

## Scope

Create a feature-flag-ready, presentation-only CQRP Decision Workstation design system. It does not alter COA mathematics, FYERS collection, persistence, validation, signal generation, risk, or paper execution.

## Display contract

- The primary cockpit displays only fresh, explainable, decision-relevant metrics.
- A missing provider field is hidden from the cockpit; it is not rendered as an empty metric.
- Derived evidence must state its maturity: `UPCOMING`, `BUILDING`, or `QUALIFIED`.
- Confidence is not described as a statistical probability until independently qualified completed paper-trade evidence exists.
- Combined 18-scenario tracking is labelled `Shadow Evidence — Building` until qualified.

## Rollout

The existing Dashboard 2.0 pages remain unchanged. Sprint 301 will use these components to implement the fixed shell and Live Cockpit behind a feature flag.
