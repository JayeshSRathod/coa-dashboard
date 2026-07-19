"""Stable contracts for versioned CQRP research analysis engines."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from .models import COAResearchResult


@runtime_checkable
class AnalysisEngine(Protocol):
    """A deterministic research engine that analyses one persisted snapshot."""

    engine_version: str

    def analyze(
        self,
        snapshot: Mapping[str, Any],
        *,
        experiment_id: str | None = None,
    ) -> COAResearchResult:
        """Return a typed result without mutating the supplied snapshot."""
