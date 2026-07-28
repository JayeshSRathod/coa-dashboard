"""Application boundary for the advisory-only CQRP Copilot."""

from __future__ import annotations
from src.copilot.models import EvidenceReference, PERSONAS
from src.copilot.llm_gateway import OllamaAdvisoryGateway
from src.copilot.research_packet import ResearchEvidenceSource, ResearchPacketBuilder
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

    def local_ollama_status(self, *, enabled: bool = False,
                            models: tuple[str, ...] = ("qwen3:0.6b", "mistral:latest", "gemma4:latest")) -> dict:
        if not enabled:
            return {
                "mode": "LOCAL_OLLAMA_ADVISORY", "enabled": False, "reachable": False,
                "available_models": [], "recommended_models": {model: False for model in models},
                "reason": "Local Ollama advisory is disabled in CQRP Configuration.",
            }
        gateway = OllamaAdvisoryGateway(model=models[0])
        try:
            available = gateway.available_models()
            return {"mode": "LOCAL_OLLAMA_ADVISORY", "enabled": True, "reachable": True, "available_models": list(available),
                    "recommended_models": {model: model in available for model in models}}
        except RuntimeError as exc:
            return {"mode": "LOCAL_OLLAMA_ADVISORY", "enabled": True, "reachable": False, "available_models": [],
                    "recommended_models": {model: False for model in models}, "reason": str(exc)}

    def local_research_report(self, source: ResearchEvidenceSource, *, session_id: str,
                              instrument: str, expiry: str | None, model: str,
                              question: str = "Summarize the recorded market structure, cite evidence, and propose only a paper-research experiment.",
                              enabled: bool = False) -> dict:
        """Generate a local advisory report from read-only persisted CQRP evidence."""
        if not enabled:
            raise RuntimeError("Local Ollama advisory is disabled in CQRP Configuration.")
        evidence = ResearchPacketBuilder().build(source, instrument=instrument, session_id=session_id, expiry=expiry)
        if not evidence:
            return {"accepted": False, "answer": "No CQRP structure evidence matches the selected session, instrument, and expiry.",
                    "evidence_ids": [], "mode": "LOCAL_OLLAMA_ADVISORY"}
        for item in evidence:
            self.copilot.record_evidence(item)
        local = OfflineCopilotService(repository=self.copilot.repository, gateway=OllamaAdvisoryGateway(model=model))
        response = local.ask(session_id=session_id, persona="RESEARCH", question=question,
                             evidence_ids=tuple(item.evidence_id for item in evidence))
        return {"response_id": response.response_id, "answer": response.answer, "accepted": response.accepted,
                "confidence": response.confidence, "evidence_ids": list(response.evidence_ids),
                "mode": "LOCAL_OLLAMA_ADVISORY", "model": model, "training": "NONE_RETRIEVAL_ONLY"}
