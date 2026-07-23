"""Small, deterministic evidence graph used by offline Copilot answers."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import EvidenceReference


class EvidenceGraph:
    def __init__(self, evidence: Iterable[EvidenceReference] = ()) -> None:
        self._records = {item.evidence_id: item for item in evidence}
        self._by_entity: dict[tuple[str, str], set[str]] = defaultdict(set)
        for item in self._records.values():
            self._by_entity[(item.entity_type, item.entity_id)].add(item.evidence_id)

    def add(self, item: EvidenceReference) -> EvidenceReference:
        existing = self._records.get(item.evidence_id)
        if existing is not None:
            return existing
        self._records[item.evidence_id] = item
        self._by_entity[(item.entity_type, item.entity_id)].add(item.evidence_id)
        return item

    def get(self, evidence_id: str) -> EvidenceReference | None:
        return self._records.get(evidence_id)

    def for_entity(self, entity_type: str, entity_id: str) -> tuple[EvidenceReference, ...]:
        return tuple(self._records[item] for item in sorted(self._by_entity[(entity_type, entity_id)]))
