"""Unit and local integration coverage for Sprint-018.1 configuration safety."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.configuration_console import ConfigurationConsoleService, InMemorySecretStore, UnsafeExecutionModeError
from src.configuration_console.secrets import CompositeSecretStore, SecretStoreUnavailable


class ConfigurationConsoleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.path = Path(self.temporary.name) / "configuration.json"
        self.secrets = InMemorySecretStore()
        self.service = ConfigurationConsoleService(configuration_path=self.path, secret_store=self.secrets)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_credentials_are_masked_and_never_written_to_configuration_history(self) -> None:
        self.service.save_broker("dhan", enabled=True, credentials={
            "client_id": "dhan-client", "access_token": "dhan-secret-token",
        })
        persisted = self.path.read_text(encoding="utf-8")
        public = self.service.public_configuration()
        self.assertNotIn("dhan-client", persisted)
        self.assertNotIn("dhan-secret-token", persisted)
        self.assertTrue(public["brokers"]["dhan"]["credentials"]["client_id"])
        self.assertTrue(public["brokers"]["dhan"]["credentials"]["access_token"])
        self.assertEqual(self.secrets.get("CQRP_DHAN_ACCESS_TOKEN"), "dhan-secret-token")

    def test_live_execution_is_rejected_and_paper_is_enforced_safe(self) -> None:
        with self.assertRaises(UnsafeExecutionModeError):
            self.service.save_execution_mode("LIVE")
        execution = self.service.save_execution_mode("PAPER")
        self.assertEqual(execution["execution_mode"], "PAPER")
        self.assertFalse(execution["trading_enabled"])
        self.assertTrue(execution["kill_switch"])
        self.assertTrue(execution["dry_run"])

    def test_connection_test_is_safe_and_version_history_is_sanitised(self) -> None:
        self.service.save_broker("telegram", enabled=True, credentials={
            "bot_token": "telegram-token", "chat_id": "chat-123",
        })
        result = self.service.test_connection("telegram")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "READY")
        self.assertGreaterEqual(data["version"], 2)
        self.assertNotIn("telegram-token", json.dumps(data))
        self.assertEqual(data["history"][-1]["action"], "connection_test")

    def test_operations_validation_and_broker_disable_are_persisted(self) -> None:
        self.service.save_broker("fyers", enabled=False, credentials={})
        operations = self.service.save_operations(scanner_interval_seconds=30, max_open_positions=2)
        state = self.service.public_configuration()
        self.assertFalse(state["brokers"]["fyers"]["enabled"])
        self.assertEqual(operations["scanner_interval_seconds"], 30)
        with self.assertRaises(ValueError):
            self.service.save_operations(scanner_interval_seconds=0, max_open_positions=2)

    def test_fyers_daily_session_values_are_masked_and_not_persisted(self) -> None:
        self.service.save_broker("fyers", enabled=True, credentials={
            "app_id": "FYERS-APP-200", "secret_key": "fyers-secret",
            "redirect_uri": "https://localhost/callback", "access_token": "daily-token",
        })
        stored = self.path.read_text(encoding="utf-8")
        public = self.service.public_configuration()["brokers"]["fyers"]
        self.assertNotIn("daily-token", stored)
        self.assertNotIn("fyers-secret", stored)
        self.assertTrue(all(public["credentials"].values()))
        self.assertEqual(self.secrets.get("CQRP_FYERS_ACCESS_TOKEN"), "daily-token")

    def test_unavailable_local_keyring_is_treated_as_absent_for_reading(self) -> None:
        class UnavailableStore:
            def get(self, name):
                raise SecretStoreUnavailable("no backend")

            def set(self, name, value):
                raise SecretStoreUnavailable("no backend")

        store = CompositeSecretStore(environment=InMemorySecretStore(), local=UnavailableStore())
        self.assertIsNone(store.get("CQRP_DHAN_ACCESS_TOKEN"))
