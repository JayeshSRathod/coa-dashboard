"""Configuration application service with a strict no-live-execution boundary."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .secrets import CompositeSecretStore, SecretStore


ALLOWED_EXECUTION_MODES = frozenset({"DISABLED", "PAPER"})
BROKER_FIELDS = {
    "dhan": ("client_id", "access_token"),
    "fyers": ("client_id", "secret_key", "redirect_uri"),
    "telegram": ("bot_token", "chat_id"),
}


class UnsafeExecutionModeError(ValueError):
    """Raised when any execution mode outside the research-safe allowlist is requested."""


class ConfigurationConsoleService:
    """Keeps runtime settings local, versioned, auditable, and free of raw secrets."""

    def __init__(self, *, configuration_path: Path | None = None,
                 secret_store: SecretStore | None = None,
                 logger: logging.Logger | None = None,
                 now: Callable[[], datetime] | None = None) -> None:
        self.configuration_path = configuration_path or Path(
            os.getenv("CQRP_CONFIGURATION_PATH", Path.home() / ".cqrp" / "configuration.json")
        )
        self.secret_store = secret_store or CompositeSecretStore()
        self.logger = logger or logging.getLogger("cqrp.configuration")
        self.now = now or (lambda: datetime.now(timezone.utc))

    def public_configuration(self) -> dict[str, Any]:
        state = self._read_state()
        brokers = {}
        for provider, fields in BROKER_FIELDS.items():
            settings = state["brokers"].get(provider, {})
            brokers[provider] = {
                "enabled": bool(settings.get("enabled", False)),
                "credentials": {field: bool(self.secret_store.get(self._secret_name(provider, field))) for field in fields},
                "last_test": dict(settings.get("last_test", {"status": "NOT_TESTED"})),
            }
        return {
            "version": state["version"],
            "brokers": brokers,
            "execution": dict(state["execution"]),
            "operations": dict(state["operations"]),
            "history": list(state["history"]),
        }

    def save_broker(self, provider: str, *, enabled: bool,
                    credentials: Mapping[str, str | None], actor: str = "local-dashboard") -> dict[str, Any]:
        provider = self._provider(provider)
        allowed_fields = BROKER_FIELDS[provider]
        for field, value in credentials.items():
            if field not in allowed_fields:
                raise ValueError(f"Unsupported {provider} credential field: {field}")
            if value:
                self.secret_store.set(self._secret_name(provider, field), value)

        state = self._read_state()
        state["brokers"][provider] = {
            "enabled": bool(enabled),
            "last_test": dict(state["brokers"].get(provider, {}).get("last_test", {"status": "NOT_TESTED"})),
        }
        self._record(state, "broker_settings_saved", provider, actor, {
            "enabled": bool(enabled),
            "credential_fields_updated": sorted(field for field, value in credentials.items() if value),
        })
        self._write_state(state)
        return self.public_configuration()["brokers"][provider]

    def save_execution_mode(self, mode: str, *, actor: str = "local-dashboard") -> dict[str, Any]:
        normalized = mode.upper().strip()
        if normalized not in ALLOWED_EXECUTION_MODES:
            raise UnsafeExecutionModeError("Only DISABLED and PAPER execution modes are permitted.")
        state = self._read_state()
        state["execution"] = {
            "execution_mode": normalized,
            "trading_enabled": False,
            "kill_switch": True,
            "dry_run": True,
        }
        self._record(state, "execution_mode_saved", "execution", actor, {"execution_mode": normalized})
        self._write_state(state)
        return dict(state["execution"])

    def save_operations(self, *, scanner_interval_seconds: int, max_open_positions: int,
                        actor: str = "local-dashboard") -> dict[str, Any]:
        if scanner_interval_seconds <= 0 or max_open_positions < 0:
            raise ValueError("Scanner interval must be positive and max open positions cannot be negative.")
        state = self._read_state()
        state["operations"] = {
            "scanner_interval_seconds": int(scanner_interval_seconds),
            "max_open_positions": int(max_open_positions),
        }
        self._record(state, "operations_saved", "operations", actor, dict(state["operations"]))
        self._write_state(state)
        return dict(state["operations"])

    def test_connection(self, provider: str, *, actor: str = "local-dashboard") -> dict[str, str]:
        provider = self._provider(provider)
        public = self.public_configuration()["brokers"][provider]
        required = BROKER_FIELDS[provider]
        if not public["enabled"]:
            result = {"status": "DISABLED", "message": "Broker is disabled; no connection attempt was made."}
        elif not all(public["credentials"].get(field) for field in required):
            result = {"status": "NOT_CONFIGURED", "message": "Required credentials are missing."}
        else:
            result = {
                "status": "READY",
                "message": "Credential presence verified. Network broker calls remain disabled in Dashboard 2.0.",
            }
        state = self._read_state()
        state["brokers"].setdefault(provider, {"enabled": False})["last_test"] = {
            **result,
            "tested_at": self._timestamp(),
        }
        self._record(state, "connection_test", provider, actor, {"status": result["status"]})
        self._write_state(state)
        self.logger.info("configuration_connection_test provider=%s status=%s", provider, result["status"])
        return result

    @staticmethod
    def _provider(provider: str) -> str:
        normalized = provider.lower().strip()
        if normalized not in BROKER_FIELDS:
            raise ValueError(f"Unsupported provider: {provider}")
        return normalized

    @staticmethod
    def _secret_name(provider: str, field: str) -> str:
        return f"CQRP_{provider}_{field}".upper()

    def _read_state(self) -> dict[str, Any]:
        default = {
            "version": 0,
            "brokers": {},
            "execution": {"execution_mode": "DISABLED", "trading_enabled": False, "kill_switch": True, "dry_run": True},
            "operations": {"scanner_interval_seconds": 60, "max_open_positions": 0},
            "history": [],
        }
        if not self.configuration_path.exists():
            return default
        try:
            stored = json.loads(self.configuration_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("The local configuration file cannot be read safely.") from exc
        return {**default, **stored}

    def _write_state(self, state: dict[str, Any]) -> None:
        self.configuration_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.configuration_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
        temporary.replace(self.configuration_path)

    def _record(self, state: dict[str, Any], action: str, subject: str, actor: str,
                details: Mapping[str, Any]) -> None:
        state["version"] = int(state.get("version", 0)) + 1
        safe_details = dict(details)
        fingerprint = hashlib.sha256(json.dumps(safe_details, sort_keys=True).encode()).hexdigest()
        state.setdefault("history", []).append({
            "version": state["version"], "action": action, "subject": subject,
            "actor": actor, "occurred_at": self._timestamp(), "details": safe_details,
            "fingerprint": fingerprint,
        })
        state["history"] = state["history"][-100:]
        self.logger.info("configuration_audit action=%s subject=%s version=%s", action, subject, state["version"])

    def _timestamp(self) -> str:
        return self.now().isoformat()
