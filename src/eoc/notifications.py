"""Optional, explicitly disabled-by-default operational notifications."""

from __future__ import annotations

from typing import Callable


class NotificationRouter:
    """Routes alerts through injected channels, recording every attempted delivery."""

    def __init__(self, repository, logger, channels: dict[str, Callable] | None = None,
                 enabled: bool = False, enabled_channels: tuple[str, ...] = ()) -> None:
        self.repository = repository
        self.logger = logger
        self.channels = dict(channels or {})
        self.enabled = enabled
        self.enabled_channels = set(enabled_channels)

    def route(self, alert) -> list[dict]:
        deliveries = []
        for channel_name in sorted(self.channels):
            delivery = {"channel": channel_name, "alert_id": alert.alert_id,
                        "status": "SKIPPED", "reason": "notifications_disabled"}
            if self.enabled and channel_name in self.enabled_channels:
                try:
                    self.channels[channel_name](alert)
                    delivery["status"], delivery["reason"] = "SENT", None
                except Exception as exc:
                    delivery["status"], delivery["reason"] = "FAILED", type(exc).__name__
            deliveries.append(self.repository.append(delivery))
            self.logger.info({"event": "eoc_notification", **delivery})
        return deliveries
