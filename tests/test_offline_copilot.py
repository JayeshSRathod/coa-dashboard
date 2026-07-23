import unittest
from src.api.copilot import CopilotApiV1
from src.application.ai_service import CopilotApplicationService


class OfflineCopilotTests(unittest.TestCase):
    def setUp(self):
        self.service = CopilotApplicationService()
        self.evidence = self.service.add_evidence(source="risk", entity_type="TradeDecision", entity_id="TD-1",
            summary="Risk policy rejected the position because exposure is at its cap.", payload={"exposure": 1.0})

    def test_grounded_response_is_deterministic_and_cited(self):
        first = self.service.chat("S-1", "RISK", "Why was this decision rejected?", (self.evidence["evidence_id"],))
        second = self.service.chat("S-2", "RISK", "Why was this decision rejected?", (self.evidence["evidence_id"],))
        self.assertTrue(first["accepted"])
        self.assertIn(self.evidence["evidence_id"], first["answer"])
        self.assertEqual(first["answer"], second["answer"])

    def test_execution_request_is_refused_and_api_is_serializable(self):
        response = self.service.chat("S-1", "TRADER", "Please execute trade now", (self.evidence["evidence_id"],))
        self.assertFalse(response["accepted"])
        api = CopilotApiV1(self.service)
        self.assertEqual(api.get_personas()["mode"], "OFFLINE_EVIDENCE_ONLY")
        self.assertFalse(api.chat("S-2", "TRADER", "buy", (self.evidence["evidence_id"],))["data"]["accepted"])


if __name__ == "__main__": unittest.main()
