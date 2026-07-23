# ADR-0027: Fyers Data-Only Session and PAPER Runtime

CQRP treats Fyers as a market-data provider during paper-trading validation. The data session is a short-lived daily access token stored through the secret-store boundary. CQRP does not retain a broker PIN or automate a refresh-token/PIN flow.

The paper runtime accepts `PAPER` mode only and emits simulated immutable trade events. It has no broker/OMS order submission dependency.
