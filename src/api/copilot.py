"""Serializable, read/advisory-only API facade for the offline Copilot."""

from __future__ import annotations
from src.application.ai_service import CopilotApplicationService


class CopilotApiV1:
    prefix = "/api/v1/copilot"
    def __init__(self, service: CopilotApplicationService) -> None: self.service = service
    def get_personas(self) -> dict: return {"status": 200, "data": list(self.service.personas()), "mode": "OFFLINE_EVIDENCE_ONLY"}
    def chat(self, session_id: str, persona: str, question: str, evidence_ids: tuple[str, ...] = ()) -> dict:
        return {"status": 200, "data": self.service.chat(session_id, persona, question, evidence_ids), "mode": "OFFLINE_EVIDENCE_ONLY"}
