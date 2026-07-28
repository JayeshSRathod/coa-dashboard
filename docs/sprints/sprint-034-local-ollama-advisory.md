# Sprint 034 — Local Ollama Advisory Research

## Purpose

Connect CQRP's existing evidence-only Copilot to an optional Ollama server on
`127.0.0.1`. The integration is read-only and advisory-only.

## Modes

- `OFFLINE_EVIDENCE_ONLY` remains the default deterministic Copilot mode.
- `LOCAL_OLLAMA_ADVISORY` is disabled by default. It can be enabled only in
  **Configuration → Local AI**, then activated by manually generating a report.
  When disabled, CQRP does not probe, contact, or load Ollama.

## Evidence contract

The research packet is constructed only from persisted CQRP dynamic structure
events and CE/PE wall records, scoped by instrument, session and optional
expiry. It contains event IDs, snapshot IDs, strikes, expiry, moving-level
evidence, and five-minute outcomes. The model must cite the supplied evidence.
The initial daily packet is deliberately compact (session summary, two notable
events and one wall); full-session detail remains in CQRP exports and can be
used by a later background-report job.

## Safety

The model does not train itself from CQRP data. Each report uses retrieval over
the selected evidence at request time. The gateway has no database write,
broker, signal, risk, paper-trading or execution dependency. It cannot apply a
parameter change; it may only propose a paper-research experiment.

## Recommended local models

- `mistral:latest` for daily session reports.
- `gemma4:latest` for slower, multi-session reviews.
- `qwen3:0.6b` for short, lower-resource summaries.
