# Sprint-031: Fyers Data-Only Session & PAPER Runtime

This sprint replaces the PIN/refresh-token assumption in CQRP's new configuration path with a daily, short-lived Fyers access-token model stored outside Git and SQLite plaintext fields. It adds a data-only provider factory and a deterministic PAPER-only runtime coordinator for the event-sourced execution engine.

No broker order endpoint, live execution mode, automated Fyers login, broker PIN storage, or refresh-token storage is introduced.
