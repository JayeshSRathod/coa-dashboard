"""Explicit primary/fallback routing for normalized market providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .contracts import MarketDataProvider, OptionChainRequest
from .models import OptionChainSnapshot, SourceTransition


class AllProvidersUnavailable(RuntimeError):
    pass


@dataclass
class MarketDataRouter:
    providers: tuple[MarketDataProvider, ...]
    transition_sink: Callable[[SourceTransition], Any] | None = None
    health_sink: Callable[[Any], Any] | None = None
    _active_provider: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.providers:
            raise ValueError("at least one provider is required")
        self._active_provider = {}

    def fetch_option_chain(self, request: OptionChainRequest) -> OptionChainSnapshot:
        errors: list[str] = []
        for provider in self.providers:
            health = provider.health()
            if health.circuit_state.value == "OPEN":
                errors.append(f"{provider.name}: circuit open")
                self._emit_health(health)
                continue
            try:
                snapshot = provider.fetch_option_chain(request)
            except Exception as exc:
                errors.append(f"{provider.name}: {type(exc).__name__}")
                self._emit_health(provider.health())
                continue
            self._emit_health(provider.health())
            previous = self._active_provider.get(request.instrument_id)
            if previous != provider.name:
                reason = "fallback_after_provider_failure" if errors else ("initial_provider_selected" if previous is None else "provider_priority_changed")
                transition = SourceTransition.new(instrument_id=request.instrument_id, from_provider=previous, to_provider=provider.name, reason=reason)
                if self.transition_sink:
                    self.transition_sink(transition)
                self._active_provider[request.instrument_id] = provider.name
            return snapshot
        raise AllProvidersUnavailable("; ".join(errors) or "no provider is available")

    def _emit_health(self, health: Any) -> None:
        if self.health_sink:
            self.health_sink(health)
