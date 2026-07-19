# ADR-0009: Live Execution Gateway and Order Management

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-010

## Decision

CQRP uses a broker-agnostic execution gateway with immutable order identities and append-only lifecycle events. Broker adapters contain transport translation only and must not reference research, signal, risk, or paper-trading modules.

## Safety

Execution defaults to DISABLED. PAPER and SIMULATION create synthetic lifecycle evidence only. LIVE mode is the sole path that may call an adapter and requires explicit trading enablement, inactive kill switch/emergency stop, disabled dry-run, valid approval reference, order limits, and configured trading hours.

## Fyers integration

The Fyers adapter accepts an injected access token or an explicit provider built from the existing authentication utility. It does not persist, return, or log credentials.

## Consequences

- Historical order replay remains deterministic from event records.
- Broker synchronization is a separate, read-only service.
- Dhan and Zerodha remain contract-only until their transport behavior is separately validated.
- No upstream strategy or existing paper-execution behavior is changed.
