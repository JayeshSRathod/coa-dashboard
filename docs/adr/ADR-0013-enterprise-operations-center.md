# ADR-0013: Enterprise Operations Center

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-014

## Decision
CQRP will use a repository-backed Enterprise Operations Center (EOC) to collect
append-only operational observations. The EOC is an observational control plane,
not a trading or research engine.

## Health and alerts
Components publish immutable health observations. Alert deduplication is by a
caller-provided key; an alert is evidence, never an automatic remediation
command. Health states are HEALTHY, WARNING, DEGRADED, FAILED, and OFFLINE.

## Audit and scheduler governance
Audit, scheduler, configuration-history, diagnostic, metric, and notification
records are append-only and protected by SQLite triggers. Configuration records
describe an observed configuration; the EOC does not apply or roll back one.

## Notification strategy
Channels are injected. External delivery is disabled by default and every
attempt, including an intentionally skipped one, is recorded.

## Consequences
Dashboard APIs read repository projections only. The EOC cannot mutate CQRP
research results, signal decisions, risk decisions, order state, trading
behavior, or analytics. No auto-remediation is implemented.
