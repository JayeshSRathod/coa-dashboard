"""Pure functions for weighted evidence scoring and research classifications."""

from __future__ import annotations

from collections.abc import Mapping


def weighted_score(scores: Mapping[str, float], weights: Mapping[str, float]) -> float:
    if set(scores) != set(weights):
        raise ValueError("scores and weights must use the same component names")
    if any(not 0 <= float(score) <= 100 for score in scores.values()):
        raise ValueError("component scores must be between 0 and 100")
    if any(float(weight) < 0 for weight in weights.values()):
        raise ValueError("weights cannot be negative")
    if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0")
    return round(sum(float(scores[name]) * float(weights[name]) for name in scores), 4)


def confidence_band(score: float) -> str:
    if not 0 <= score <= 100:
        raise ValueError("confidence score must be between 0 and 100")
    if score < 40:
        return "WEAK"
    if score < 60:
        return "MODERATE"
    if score < 75:
        return "GOOD"
    if score < 90:
        return "STRONG"
    return "EXCEPTIONAL"
