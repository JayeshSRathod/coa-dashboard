"""Stable contracts for CQRP validation components."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from src.coa.models import COAResearchResult

from .models import ComponentAssessment


class ValidationComponent(Protocol):
    """A deterministic evidence evaluator with no persistence or trade side effects."""

    name: str

    def assess(
        self, snapshot: Mapping[str, Any], coa_result: COAResearchResult
    ) -> ComponentAssessment:
        """Return score, reasons, warnings, and serialisable details."""
