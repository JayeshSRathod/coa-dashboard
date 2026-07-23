"""Application boundary for the advisory-only CQRP Copilot."""

from __future__ import annotations
from src.copilot.models import EvidenceReference, PERSONAS
from src.copilot.service import OfflineCopilotService


class CopilotApplicationService:
    def __init__(self, copilot: OfflineCopilotService | None = None) -> None:
        self.copilot = copilot or OfflineCopilotService()

    def add_evidence(self, **values) -> dict:
        item = self.copilot.record_evidence(EvidenceReference.new(**values))
        return {"evidence_id": item.evidence_id, "source": item.source, "summary": item.summary}

    def chat(self, session_id: str, persona: str, question: str, evidence_ids: tuple[str, ...] = ()) -> dict:
        response = self.copilot.ask(session_id=session_id, persona=persona, question=question, evidence_ids=evidence_ids)
        return {"response_id": response.response_id, "persona": response.persona, "answer": response.answer,
                "evidence_ids": list(response.evidence_ids), "confidence": response.confidence, "accepted": response.accepted}

    def personas(self) -> tuple[str, ...]:
        return PERSONAS
