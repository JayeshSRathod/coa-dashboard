# ADR-0021: Canonical COA engine

Sprint-020 adds an additive canonical COA facade. It invokes frozen COA 1.0 and COA 2.0 functions, translates their documented outputs into immutable state contracts, and makes the structural/tactical compatibility table explicit. It does not alter `engine/coa_math.py`, issue orders, or replace the existing research pipeline.

Canonical output is deterministic for an identical normalized snapshot and metadata history. Replay comparison verifies that structural values match the frozen baseline before later orchestration consumes them.
