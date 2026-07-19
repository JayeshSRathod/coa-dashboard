# ADR-0014: Advanced Portfolio & Options Analytics

- Status: Accepted
- Date: 2026-07-19

CQRP uses pure mathematical calculators and append-only analysis repositories for
portfolio and derivatives insights. Greeks use deterministic Black-Scholes inputs;
option-chain/OI/IV/max-pain outputs are derived only from supplied data. Stress
tests apply explicit scenario shocks. Analytics cannot create orders, hedge, or
modify positions. Future exchanges require adapters that supply the same inputs.
