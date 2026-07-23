from __future__ import annotations
import unittest
from src.api import CQRPApiV1
from src.application import InMemoryEventBus
from src.application.services import DecisionService
from src.decision.models import TradeDecision
class ApplicationApiTests(unittest.TestCase):
    def test_service_exposes_dto_and_publishes_event(self):
        bus, service = InMemoryEventBus(), DecisionService(); service.event_bus = bus
        decision = TradeDecision.new(snapshot_id="s1", instrument="NIFTY", action="NO_TRADE", expiry=None, strike=None, option_type=None, entry=None, stop_loss=None, target_1=None, target_2=None, quantity=0, confidence=0, valid_until="2026-07-23T10:05:00Z", status="REJECTED", rule_version="1.0", metadata={"execution_mode":"DISABLED"})
        dto = service.publish_decision(decision); api = CQRPApiV1(service)
        self.assertEqual(bus.events[0].event_type, "DecisionCreated"); self.assertEqual(api.get_decision(dto.decision_id)["data"]["execution_mode"], "DISABLED"); self.assertEqual(api.get_system()["data"]["api_version"], "v1")
