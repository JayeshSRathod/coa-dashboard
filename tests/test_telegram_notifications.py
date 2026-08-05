"""Deterministic tests for Telegram PAPER-research reporting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from src.application.fyers_worker import UniverseCycle, WorkerCycle
from src.configuration_console import ConfigurationConsoleService, InMemorySecretStore
from src.notifications import ResearchReportDispatcher, TelegramNotificationClient


class FakeTransport:
    def __init__(self) -> None:
        self.messages = []

    def send(self, **kwargs) -> None:
        self.messages.append(kwargs)


class TelegramNotificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        service = ConfigurationConsoleService(
            configuration_path=Path(self.temporary.name) / "configuration.json",
            secret_store=InMemorySecretStore(),
        )
        service.save_broker("telegram", enabled=True, credentials={"bot_token": "token", "chat_id": "chat"})
        service.save_telegram_notifications(enabled=True, heartbeat_minutes=30, topics={
            "system_health": 10, "preclose_plan": 20, "paper_portfolio": 30, "daily_research": 40,
        })
        self.transport = FakeTransport()
        self.client = TelegramNotificationClient(service, transport=self.transport)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_routes_to_configured_topic_without_exposing_secrets(self) -> None:
        result = self.client.send("system_health", "safe message")
        self.assertEqual(result.status, "SENT")
        self.assertEqual(self.transport.messages[0]["topic_id"], 10)
        self.assertEqual(self.transport.messages[0]["text"], "safe message")
        self.assertEqual(self.transport.messages[0]["bot_token"], "token")

    def test_dispatcher_reports_start_plan_paper_event_heartbeat_and_daily_close(self) -> None:
        current = datetime(2026, 8, 5, 4, 0, tzinfo=timezone.utc)
        dispatcher = ResearchReportDispatcher(self.client, now=lambda: current)
        outcome = SimpleNamespace(snapshot_id="snapshot-1", trade_plan_id="plan-1", paper_trade_id="trade-1")
        dispatcher.observe_cycle(UniverseCycle("cycle", (WorkerCycle("2026-08-05T04:00:00+00:00", outcome, instrument_id="NIFTY"),)))
        self.assertEqual([item["topic_id"] for item in self.transport.messages], [10, 20, 30])
        current += timedelta(minutes=30)
        dispatcher.observe_cycle(UniverseCycle("cycle", (WorkerCycle("2026-08-05T04:30:00+00:00", outcome, instrument_id="NIFTY"),)))
        self.assertIn("health heartbeat", self.transport.messages[-1]["text"])
        closing = dispatcher.close_session()
        self.assertEqual(closing.status, "SENT")
        self.assertEqual(self.transport.messages[-1]["topic_id"], 40)
        self.assertIn("Snapshots captured: NIFTY 2", self.transport.messages[-1]["text"])

    def test_duplicate_capture_failure_is_not_repeated(self) -> None:
        dispatcher = ResearchReportDispatcher(self.client)
        cycle = UniverseCycle("cycle", (WorkerCycle("now", None, "token missing", "BANKNIFTY"),))
        dispatcher.observe_cycle(cycle)
        dispatcher.observe_cycle(cycle)
        warnings = [message for message in self.transport.messages if "capture warning" in message["text"]]
        self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()
