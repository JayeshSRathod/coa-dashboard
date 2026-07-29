"""Provider contract and deterministic offline gateway."""

from __future__ import annotations

import json
import os
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen
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


class OllamaAdvisoryGateway:
    """Local-only, evidence-grounded Ollama gateway with no CQRP write authority."""

    _BLOCKED_INTENTS = ("buy", "sell", "place", "execute", "modify risk", "approve", "order")

    def __init__(self, *, model: str = "mistral:latest", base_url: str | None = None,
                 timeout_seconds: float = 180.0) -> None:
        self.model = model
        self.base_url = (base_url or os.getenv("CQRP_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def available_models(self) -> tuple[str, ...]:
        payload = self._get("/api/tags")
        return tuple(str(item.get("name")) for item in payload.get("models", ()) if item.get("name"))

    def is_available(self) -> bool:
        try:
            return self.model in self.available_models()
        except RuntimeError:
            return False

    def respond(self, persona: str, question: str, context: EvidenceContext) -> str:
        if any(term in question.lower() for term in self._BLOCKED_INTENTS):
            return "I cannot create trades, approve execution, or change CQRP controls. I can only explain recorded evidence."
        if not context.evidence:
            return "No authoritative CQRP evidence was supplied for this question."
        evidence = [
            {"evidence_id": item.evidence_id, "source": item.source, "entity_type": item.entity_type,
             "entity_id": item.entity_id, "summary": item.summary, "payload": dict(item.payload)}
            for item in context.evidence
        ]
        prompt = {
            "role": "CQRP local research analyst",
            "persona": persona,
            "rules": [
                "Use only the supplied CQRP evidence.",
                "Do not issue a buy, sell, order, execution, risk-override, or parameter-change instruction.",
                "Describe hypotheses as experiments, never as applied rules.",
                "Cite every conclusion using evidence IDs in square brackets.",
                "State contradictory or missing evidence when present.",
                "Return at most 40 words as compact valid JSON with finding, uncertainty, and experiment fields.",
            ],
            "question": question,
            "evidence": evidence,
        }
        response = self._post("/api/chat", {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": json.dumps(prompt, sort_keys=True, default=str)}],
            "options": {"temperature": 0, "num_predict": 32},
        })
        content = str(((response.get("message") or {}).get("content") or "")).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty advisory response")
        citations = " ".join(f"[{item.evidence_id}]" for item in context.evidence)
        return f"{content}\n\nCQRP evidence: {citations}"

    def _get(self, path: str) -> dict:
        try:
            with urlopen(f"{self.base_url}{path}", timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Local Ollama is unavailable: {exc}") from exc

    def _post(self, path: str, payload: dict) -> dict:
        request = Request(f"{self.base_url}{path}", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Local Ollama advisory request failed: {exc}") from exc
