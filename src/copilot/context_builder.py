"""Bounded, evidence-only prompt context construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import EvidenceReference


@dataclass(frozen=True)
class EvidenceContext:
    evidence: tuple[EvidenceReference, ...]
    truncated: bool


class ContextBuilder:
    def build(self, evidence: Iterable[EvidenceReference], *, limit: int = 8) -> EvidenceContext:
        if limit < 1:
            raise ValueError("evidence limit must be positive")
        ordered = tuple(sorted(evidence, key=lambda item: (item.source, item.entity_type, item.entity_id, item.evidence_id)))
        return EvidenceContext(ordered[:limit], len(ordered) > limit)
