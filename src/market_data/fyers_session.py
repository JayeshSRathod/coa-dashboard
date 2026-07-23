"""Secure data-only Fyers session boundary.

This module does not submit broker orders. A user completes FYERS' daily
interactive authentication outside CQRP and supplies the resulting short-lived
access token through the secure configuration store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.configuration_console.secrets import SecretStore

from .providers.fyers_provider import FyersProvider


FYERS_SECRETS = {
    "app_id": "CQRP_FYERS_APP_ID",
    "secret_key": "CQRP_FYERS_SECRET_KEY",
    "redirect_uri": "CQRP_FYERS_REDIRECT_URI",
    "access_token": "CQRP_FYERS_ACCESS_TOKEN",
}


@dataclass(frozen=True)
class FyersSessionStatus:
    ready: bool
    reason: str
    mode: str = "DATA_ONLY_PAPER"


class FyersDataSessionFactory:
    """Creates a market-data adapter only when a daily session is available."""

    def __init__(self, secret_store: SecretStore) -> None:
        self.secret_store = secret_store

    def status(self) -> FyersSessionStatus:
        missing = tuple(name for name, secret_name in FYERS_SECRETS.items() if not self.secret_store.get(secret_name))
        if missing:
            return FyersSessionStatus(False, "Missing secure Fyers values: " + ", ".join(missing))
        return FyersSessionStatus(True, "Daily Fyers data session is available.")

    def provider(self, fetcher: Callable | None = None) -> FyersProvider:
        status = self.status()
        if not status.ready:
            raise RuntimeError(status.reason)
        return FyersProvider(
            app_id=str(self.secret_store.get(FYERS_SECRETS["app_id"])),
            access_token=str(self.secret_store.get(FYERS_SECRETS["access_token"])),
            fetcher=fetcher,
        )
