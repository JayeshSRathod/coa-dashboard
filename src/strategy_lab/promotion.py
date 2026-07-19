"""Deterministic promotion recommendation calculation; promotion is always manual."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PromotionEvaluation:
    recommendation: str
    criteria: Mapping[str, float]
    evidence: Mapping[str, Any]
    failed_criteria: tuple[str, ...]


def evaluate_promotion(metrics: Mapping[str, Any], criteria: Mapping[str, float]) -> PromotionEvaluation:
    failed = []
    for name, threshold in criteria.items():
        value = metrics.get(name)
        if value is None:
            failed.append(name)
        elif name == "maximum_drawdown":
            if float(value) > threshold:
                failed.append(name)
        elif float(value) < threshold:
            failed.append(name)
    return PromotionEvaluation(
        recommendation="CANDIDATE" if not failed else "REJECT",
        criteria=dict(criteria), evidence=dict(metrics), failed_criteria=tuple(failed),
    )
