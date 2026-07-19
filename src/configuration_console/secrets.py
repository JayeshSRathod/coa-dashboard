"""Secret storage boundaries. Raw values never enter CQRP configuration files."""

from __future__ import annotations

import os
from typing import Mapping, Protocol


class SecretStoreUnavailable(RuntimeError):
    """Raised when secure local secret persistence is not available."""


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...


class InMemorySecretStore:
    """Test-only store; it is deliberately never selected by application code."""

    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        self._values = dict(values or {})

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def set(self, name: str, value: str) -> None:
        self._values[name] = value


class KeyringSecretStore:
    """Persist local credentials through the operating-system credential manager."""

    def __init__(self, service_name: str = "CQRP") -> None:
        self.service_name = service_name

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:  # pragma: no cover - dependent on local runtime
            raise SecretStoreUnavailable(
                "Secure local storage needs the optional 'keyring' package. "
                "Use environment variables or Streamlit secrets until it is installed."
            ) from exc
        return keyring

    def get(self, name: str) -> str | None:
        try:
            return self._keyring().get_password(self.service_name, name)
        except Exception:
            # A cloud runtime may not provide an OS keyring backend. Treat that
            # as an absent local credential rather than making the dashboard fail.
            return None

    def set(self, name: str, value: str) -> None:
        if not value:
            return
        try:
            self._keyring().set_password(self.service_name, name, value)
        except Exception as exc:  # pragma: no cover - keyring backend specific
            raise SecretStoreUnavailable("The operating-system credential manager rejected the update.") from exc


class EnvironmentSecretStore:
    """Read-only environment and Streamlit secrets adapter for deployed applications."""

    def get(self, name: str) -> str | None:
        value = os.getenv(name)
        if value:
            return value
        try:
            import streamlit as st

            return st.secrets.get(name)
        except Exception:
            return None

    def set(self, name: str, value: str) -> None:
        raise SecretStoreUnavailable(
            "Environment and Streamlit secrets are read-only at runtime. "
            "Configure them in the hosting environment."
        )


class CompositeSecretStore:
    """Prefer deployment secrets for reads and OS keyring for local writes."""

    def __init__(self, *, environment: EnvironmentSecretStore | None = None,
                 local: KeyringSecretStore | None = None) -> None:
        self.environment = environment or EnvironmentSecretStore()
        self.local = local or KeyringSecretStore()

    def get(self, name: str) -> str | None:
        value = self.environment.get(name)
        if value:
            return value
        try:
            return self.local.get(name)
        except SecretStoreUnavailable:
            return None

    def set(self, name: str, value: str) -> None:
        self.local.set(name, value)
