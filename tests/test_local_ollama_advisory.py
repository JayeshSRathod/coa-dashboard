import unittest
from unittest.mock import patch

from src.application.ai_service import CopilotApplicationService
from src.copilot.context_builder import ContextBuilder
from src.copilot.llm_gateway import OllamaAdvisoryGateway
from src.copilot.models import EvidenceReference
from src.copilot.validators import validate_response
from src.copilot.models import CopilotResponse


class _GatewayUnderTest(OllamaAdvisoryGateway):
    def _get(self, path):
        self.get_path = path
        return {"models": [{"name": "mistral:latest"}, {"name": "gemma4:latest"}]}

    def _post(self, path, payload):
        self.post_path = path
        self.post_payload = payload
        return {"message": {"content": '{"finding":"evidence-backed observation"}'}}


class _Source:
    def dynamic_events(self, instrument_id, *, session_id=None, event_types=(), limit=10_000):
        return [{"event_id": "EVT-1", "instrument": instrument_id, "session_id": session_id,
                 "expiry": "2026-07-28", "event_type": "VOLUME_BURST", "occurred_at": "2026-07-28T09:20:00+05:30",
                 "scenario_track": "COA1_PLUS_COA2", "payload": {"strike": 24000, "spot": 23995}}]

    def dynamic_walls(self, instrument_id, *, session_id=None, limit=25_000):
        return [{"wall_id": "WALL-1", "instrument": instrument_id, "expiry": "2026-07-28", "captured_at": "2026-07-28T09:20:00+05:30",
                 "strike": 24000, "side": "CE", "metric": "VOLUME", "rank": 1, "metric_value": 1200,
                 "snapshot_id": "SNP-1", "payload": {"contract": "NIFTY 24000 CE expiry 2026-07-28"}}]


class _FakeLocalGateway:
    def __init__(self, *, model, **_):
        self.model = model

    def available_models(self):
        return ("mistral:latest", "gemma4:latest")

    def respond(self, persona, question, context):
        return "Local advisory finding. " + " ".join(f"[{item.evidence_id}]" for item in context.evidence)


class LocalOllamaAdvisoryTests(unittest.TestCase):
    def test_gateway_uses_local_chat_endpoint_and_cites_context(self):
        evidence = EvidenceReference.new(source="test", entity_type="event", entity_id="EVT-1", summary="Evidence")
        gateway = _GatewayUnderTest(model="mistral:latest")
        answer = gateway.respond("RESEARCH", "Summarize the evidence", ContextBuilder().build((evidence,)))
        self.assertEqual(gateway.post_path, "/api/chat")
        self.assertEqual(gateway.post_payload["model"], "mistral:latest")
        self.assertIn(f"[{evidence.evidence_id}]", answer)
        self.assertIn("evidence-backed", answer)

    @patch("src.application.ai_service.OllamaAdvisoryGateway", _FakeLocalGateway)
    def test_local_report_is_retrieval_only_and_evidence_grounded(self):
        report = CopilotApplicationService().local_research_report(
            _Source(), session_id="NIFTY:2026-07-28", instrument="NIFTY", expiry="2026-07-28", model="mistral:latest"
        )
        self.assertTrue(report["accepted"])
        self.assertEqual(report["mode"], "LOCAL_OLLAMA_ADVISORY")
        self.assertEqual(report["training"], "NONE_RETRIEVAL_ONLY")
        self.assertTrue(report["evidence_ids"])

    def test_trade_directive_is_rejected_even_with_evidence(self):
        response = CopilotResponse.new(session_id="S-1", persona="RESEARCH", question="report",
            answer="Buy NIFTY 24000 CE [EVT-1]", evidence_ids=("EVT-1",), confidence=1.0, accepted=True)
        self.assertFalse(validate_response(response).accepted)


if __name__ == "__main__":
    unittest.main()
