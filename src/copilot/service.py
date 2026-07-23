"""Advisory-only orchestration for the offline CQRP Copilot."""

from __future__ import annotations
from .context_builder import ContextBuilder
from .llm_gateway import OfflineEvidenceGateway
from .models import CopilotResponse, EvidenceReference, PERSONAS
from .repository import InMemoryCopilotRepository
from .validators import validate_response


class OfflineCopilotService:
    def __init__(self, repository: InMemoryCopilotRepository | None = None, gateway: OfflineEvidenceGateway | None = None) -> None:
        self.repository = repository or InMemoryCopilotRepository()
        self.gateway = gateway or OfflineEvidenceGateway()
        self.context_builder = ContextBuilder()

    def record_evidence(self, evidence: EvidenceReference) -> EvidenceReference:
        return self.repository.add_evidence(evidence)

    def ask(self, *, session_id: str, persona: str, question: str, evidence_ids: tuple[str, ...] = ()) -> CopilotResponse:
        if persona not in PERSONAS:
            raise ValueError("unsupported Copilot persona")
        chosen = tuple(item for item in (self.repository.get_evidence(item_id) for item_id in evidence_ids) if item is not None)
        context = self.context_builder.build(chosen)
        answer = self.gateway.respond(persona, question, context)
        response = CopilotResponse.new(session_id=session_id, persona=persona, question=question,
            answer=answer, evidence_ids=tuple(item.evidence_id for item in context.evidence),
            confidence=1.0 if context.evidence else 0.0, accepted=bool(context.evidence))
        if not validate_response(response).accepted:
            response = CopilotResponse.new(session_id=session_id, persona=persona, question=question,
                answer="I can only provide a grounded advisory response with CQRP evidence.",
                evidence_ids=(), confidence=0.0, accepted=False)
        return self.repository.append_response(response)

    def history(self, session_id: str) -> tuple[CopilotResponse, ...]:
        return self.repository.history(session_id)
