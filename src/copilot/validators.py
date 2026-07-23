"""Safety validators for evidence-backed advisory responses."""

from __future__ import annotations

from dataclasses import dataclass
from .models import CopilotResponse


_PROHIBITED = ("place order", "execute trade", "modify risk", "override risk", "approve execution")


@dataclass(frozen=True)
class ResponseValidation:
    accepted: bool
    reasons: tuple[str, ...]


def validate_response(response: CopilotResponse) -> ResponseValidation:
    answer = response.answer.lower()
    reasons = []
    if not response.evidence_ids:
        reasons.append("evidence_required")
    if any(phrase in answer for phrase in _PROHIBITED):
        reasons.append("prohibited_execution_instruction")
    if response.accepted and any(f"[{evidence_id}]" not in response.answer for evidence_id in response.evidence_ids):
        reasons.append("missing_evidence_citation")
    return ResponseValidation(not reasons, tuple(reasons))
