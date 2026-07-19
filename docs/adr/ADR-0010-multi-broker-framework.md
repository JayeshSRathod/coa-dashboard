# ADR-0010: Multi-Broker and Multi-Asset Framework

- Status: Accepted
- Date: 2026-07-19
- Sprint: Sprint-011

## Decision

CQRP represents instruments through a centralized internal registry. Broker symbols are stored only as mappings from internal instrument IDs. Broker accounts and portfolio routes are immutable records selected deterministically by priority and account eligibility.

## Architecture

The existing Sprint-010 BrokerAdapter remains the execution contract. A catalog registers Fyers, Dhan, Zerodha, and Angel One adapters; unsupported brokers are explicit placeholders. Market-data providers expose normalized source data through a separate contract. A multi-account synchronizer records only read-only broker evidence.

## Consequences

- Research modules do not parse broker symbols or choose brokers.
- Existing gateway behavior and safety controls remain unchanged.
- Automatic production failover is not implemented and is disabled by configuration.
- The registry can grow to new exchanges, asset classes, broker accounts, and providers without upstream changes.
