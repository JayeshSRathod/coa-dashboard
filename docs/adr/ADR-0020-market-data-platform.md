# ADR-0020 — Market Data Platform

`src/market_data/` is CQRP's authoritative enterprise entry point for broker-normalized market data. Provider adapters own transport only; mappers own provider-field translation only; downstream consumers receive immutable CQRP models.

Every canonical option-chain snapshot is stored append-only with source, latency, quality, and payload evidence. Provider switching is explicit through a `source_transition` record. Stale or incomplete data may be recorded for audit, but cannot enter the legacy capture/research decision path.

The original root `app.py` is a legacy Streamlit application outside Dashboard 2.0 and CQRP 3.0. It is retained as a compatibility artifact; new Dashboard 2.0 and workstation code must never import broker SDKs or broker JSON parsers.
