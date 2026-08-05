"""Minimal, secret-safe Telegram delivery adapter."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.configuration_console.service import ConfigurationConsoleService


class TelegramTransport(Protocol):
    def send(self, *, bot_token: str, chat_id: str, text: str,
             topic_id: int | None, silent: bool) -> None: ...


class UrllibTelegramTransport:
    """Use the standard library so notification support adds no dependency."""

    def send(self, *, bot_token: str, chat_id: str, text: str,
             topic_id: int | None, silent: bool) -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text, "disable_notification": silent}
        if topic_id is not None:
            payload["message_thread_id"] = topic_id
        request = Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # nosec B310 - fixed Telegram endpoint
                if not 200 <= response.status < 300:
                    raise RuntimeError("Telegram rejected the notification.")
        except URLError as exc:
            raise RuntimeError("Telegram connection failed.") from exc


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    reason: str


class TelegramNotificationClient:
    """Reads ephemeral secrets only at delivery time and never logs them."""

    def __init__(self, configuration: ConfigurationConsoleService,
                 transport: TelegramTransport | None = None,
                 logger: logging.Logger | None = None) -> None:
        self.configuration = configuration
        self.transport = transport or UrllibTelegramTransport()
        self.logger = logger or logging.getLogger("cqrp.notifications.telegram")

    def send(self, topic: str, text: str, *, silent: bool = False) -> DeliveryResult:
        settings = self.configuration.telegram_delivery_settings()
        if not settings["enabled"]:
            return DeliveryResult("SKIPPED", "Telegram reporting is disabled.")
        if not settings["bot_token"] or not settings["chat_id"]:
            return DeliveryResult("SKIPPED", "Telegram credentials are incomplete.")
        try:
            topic_id = settings["topics"].get(topic)
            self.transport.send(
                bot_token=str(settings["bot_token"]), chat_id=str(settings["chat_id"]),
                text=text, topic_id=int(topic_id) if topic_id else None, silent=silent,
            )
        except Exception as exc:
            self.logger.warning("telegram_delivery_failed topic=%s error=%s", topic, type(exc).__name__)
            return DeliveryResult("FAILED", "Telegram delivery failed; check the local configuration and connection.")
        self.logger.info("telegram_delivery_sent topic=%s", topic)
        return DeliveryResult("SENT", "Delivered.")

    def send_test(self) -> DeliveryResult:
        return self.send(
            "system_health",
            "CQRP Telegram test\nMode: PAPER ONLY\nNo broker order or live execution is enabled.",
        )
