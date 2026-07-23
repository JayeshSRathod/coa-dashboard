"""Provider contract and deterministic offline gateway."""

from __future__ import annotations

from typing import Protocol
from .context_builder import EvidenceContext


class LLMGateway(Protocol):
    def respond(self, persona: str, question: str, context: EvidenceContext) -> str: ...


class OfflineEvidenceGateway:
    """No-network implementation. It summarizes only supplied evidence."""
    _BLOCKED_INTENTS = ("buy", "sell", "place", "execute", "modify risk", "approve")

    def respond(self, persona: str, question: str, context: EvidenceContext) -> str:
        if any(term in question.lower() for term in self._BLOCKED_INTENTS):
            return "I cannot create trades, approve execution, or change CQRP controls. I can only explain recorded evidence."
        if not context.evidence:
            return "No authoritative CQRP evidence was supplied for this question."
        statements = [f"{item.summary} [{item.evidence_id}]" for item in context.evidence]
        truncated = " Additional evidence exists but was omitted by the context limit." if context.truncated else ""
        return f"{persona.title()} Copilot evidence summary: " + " ".join(statements) + truncated
