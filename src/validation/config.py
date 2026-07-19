"""Configuration for deterministic research-only validation scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ValidationConfig:
    volume_weight: float = 0.20
    oi_weight: float = 0.25
    strike_weight: float = 0.15
    liquidity_weight: float = 0.20
    market_context_weight: float = 0.20
    minimum_valid_score: float = 60.0
    stale_latency_ms: float = 3000.0
    max_futures_spot_difference_pct: float = 2.0
    validation_version: str = "1.0.0"

    def __post_init__(self) -> None:
        weights = self.weights
        if any(value < 0 for value in weights.values()):
            raise ValueError("validation weights cannot be negative")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError("validation weights must sum to 1.0")
        if not 0 <= self.minimum_valid_score <= 100:
            raise ValueError("minimum_valid_score must be between 0 and 100")
        if self.stale_latency_ms <= 0 or self.max_futures_spot_difference_pct < 0:
            raise ValueError("validation thresholds must be non-negative")

    @property
    def weights(self) -> Mapping[str, float]:
        return {
            "volume": self.volume_weight,
            "open_interest": self.oi_weight,
            "strike_quality": self.strike_weight,
            "liquidity": self.liquidity_weight,
            "market_context": self.market_context_weight,
        }
