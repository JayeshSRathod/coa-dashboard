# ADR-0001: CQRP is a platform, not a dashboard

- Status: Accepted
- Date: 2026-07-11

## Decision

CQRP is a research-first platform. The Streamlit dashboard is a presentation consumer, not the centre of the architecture.

## Consequences

The COA engine remains deterministic and independent of UI, broker APIs, and persistence. New configuration, logging, persistence, research, validation, analytics, and execution modules are introduced alongside the v1 code before any refactor of trading mathematics.