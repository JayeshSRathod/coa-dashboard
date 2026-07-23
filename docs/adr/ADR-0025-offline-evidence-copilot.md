# ADR-0025: Offline Evidence Copilot

CQRP Sprint-029 starts with an offline, deterministic Copilot. It summarizes only explicitly provided evidence and cites every accepted answer. It has no network client, API key, model SDK, broker dependency, risk mutation path, or execution capability.

An LLM provider can later implement the `LLMGateway` contract only after provider credentials, privacy requirements, evaluation, and safety approval are complete. The Copilot remains advisory-only regardless of provider.
