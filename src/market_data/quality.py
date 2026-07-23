"""Deterministic quality assessment for normalized market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import OptionChainSnapshot, QualityState


@dataclass(frozen=True)
class QualityAssessment:
    state: QualityState
    reasons: tuple[str, ...]
    age_seconds: float | None

    @property
    def decision_allowed(self) -> bool:
        return self.state in (QualityState.HEALTHY, QualityState.WARNING)


class MarketDataQualityEngine:
    def __init__(self, max_age_seconds: float = 15.0) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self.max_age_seconds = max_age_seconds

    def assess(self, snapshot: OptionChainSnapshot, now: str | None = None) -> QualityAssessment:
        reasons: list[str] = []
        try:
            captured = datetime.fromisoformat(snapshot.captured_at.replace("Z", "+00:00"))
            reference = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
            age = max(0.0, (reference - captured).total_seconds())
        except ValueError:
            return QualityAssessment(QualityState.INCOMPLETE, ("captured_at is invalid",), None)
        if age > self.max_age_seconds:
            return QualityAssessment(QualityState.STALE, (f"snapshot age {age:.3f}s exceeds {self.max_age_seconds:.3f}s",), age)
        if snapshot.spot <= 0:
            return QualityAssessment(QualityState.INCOMPLETE, ("spot must be positive",), age)
        if not snapshot.contracts:
            return QualityAssessment(QualityState.INCOMPLETE, ("option chain is empty",), age)
        calls = {item.strike for item in snapshot.contracts if item.option_type == "CE" and item.premium >= 0}
        puts = {item.strike for item in snapshot.contracts if item.option_type == "PE" and item.premium >= 0}
        if not calls or not puts:
            return QualityAssessment(QualityState.INCOMPLETE, ("option chain must include CE and PE contracts",), age)
        if calls != puts:
            reasons.append("some strikes have only one option side")
        if snapshot.latency_ms is not None and snapshot.latency_ms > 2000:
            reasons.append(f"provider latency {snapshot.latency_ms:.0f}ms is elevated")
        return QualityAssessment(QualityState.WARNING if reasons else QualityState.HEALTHY, tuple(reasons), age)
