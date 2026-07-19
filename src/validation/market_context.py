"""Deterministic freshness and market-context evidence assessment."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from src.coa.models import COAResearchResult

from .config import ValidationConfig
from .models import ComponentAssessment


def _parse(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


class MarketContextValidator:
    name = "market_context"

    def __init__(self, config: ValidationConfig) -> None:
        self.config = config

    def assess(self, snapshot: Mapping[str, object], coa_result: COAResearchResult) -> ComponentAssessment:
        score = 40
        warnings = []
        failures = []
        market_time = _parse(snapshot.get("market_captured_at") or snapshot.get("captured_at"))
        if market_time is None:
            failures.append("market capture timestamp is invalid")
        else:
            local_minutes = market_time.hour * 60 + market_time.minute
            if 9 * 60 + 15 <= local_minutes <= 15 * 60 + 30:
                score += 20
            else:
                warnings.append("snapshot is outside the normal Indian cash-market session")
        latency = snapshot.get("source_latency_ms")
        try:
            if latency is not None and float(latency) <= self.config.stale_latency_ms:
                score += 20
            elif latency is not None:
                warnings.append("source latency exceeds configured freshness threshold")
            else:
                warnings.append("source latency is unavailable")
        except (TypeError, ValueError):
            warnings.append("source latency is invalid")
        spot = snapshot.get("spot")
        futures = snapshot.get("futures_price")
        try:
            if futures is None:
                warnings.append("futures price is unavailable")
            else:
                difference = abs(float(futures) - float(spot)) / float(spot) * 100
                if difference <= self.config.max_futures_spot_difference_pct:
                    score += 20
                else:
                    warnings.append("spot and futures differ beyond the configured threshold")
        except (TypeError, ValueError, ZeroDivisionError):
            warnings.append("spot/futures consistency cannot be assessed")
        metadata = snapshot.get("metadata") or {}
        if isinstance(metadata, Mapping) and metadata.get("instrument_consistent") is False:
            failures.append("instrument metadata is inconsistent")
        elif snapshot.get("instrument"):
            score += 20
        else:
            failures.append("instrument metadata is missing")
        return ComponentAssessment.new(
            name=self.name, score=max(0, min(100, score)),
            reasons=("market context was evaluated from persisted snapshot metadata",),
            warnings=warnings, failures=failures,
            details={"market_timestamp": str(snapshot.get("market_captured_at") or snapshot.get("captured_at")),
                     "latency_ms": latency, "futures_price": futures, "spot": spot},
        )
