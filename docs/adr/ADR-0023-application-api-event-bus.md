# ADR-0023: Application API and Event Bus

Sprint-022 introduces a transport-neutral application boundary. Public API calls return DTOs rather than domain models, and the in-process event bus publishes immutable events. HTTP and WebSocket servers are adapters to be added without changing domain services. Execution remains disabled.
