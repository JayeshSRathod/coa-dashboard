"""Repository abstractions for append-only offline Copilot interactions."""

from __future__ import annotations
from .models import CopilotResponse, EvidenceReference


class InMemoryCopilotRepository:
    """Local/test store; future persistence must preserve this append-only contract."""
    def __init__(self) -> None:
        self._evidence: dict[str, EvidenceReference] = {}
        self._responses: dict[str, CopilotResponse] = {}

    def add_evidence(self, item: EvidenceReference) -> EvidenceReference:
        self._evidence.setdefault(item.evidence_id, item)
        return self._evidence[item.evidence_id]

    def get_evidence(self, evidence_id: str) -> EvidenceReference | None:
        return self._evidence.get(evidence_id)

    def append_response(self, response: CopilotResponse) -> CopilotResponse:
        self._responses.setdefault(response.response_id, response)
        return self._responses[response.response_id]

    def history(self, session_id: str) -> tuple[CopilotResponse, ...]:
        return tuple(sorted((item for item in self._responses.values() if item.session_id == session_id), key=lambda item: (item.created_at, item.response_id)))
