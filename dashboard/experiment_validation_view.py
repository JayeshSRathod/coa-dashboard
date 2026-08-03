"""Presentation read models for CQRP experiment-validation workspaces."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable, Mapping


def build_validation_cards(record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {
            "status": "NOT_AVAILABLE",
            "validation_score": None,
            "recommendation": None,
            "mode": "SHADOW_RESEARCH_ONLY",
        }
    return {
        "validation_id": record.get("validation_id"),
        "pattern_id": record.get("pattern_id"),
        "status": record.get("status"),
        "recommendation": record.get("recommendation"),
        "validation_score": record.get("validation_score"),
        "validation_sample_size": record.get("validation_sample_size"),
        "out_of_sample_win_rate": record.get("out_of_sample_win_rate"),
        "out_of_sample_expectancy_r": record.get("out_of_sample_expectancy_r"),
        "degradation_percent": record.get("degradation_percent"),
        "stability_score": record.get("stability_score"),
        "walk_forward_score": record.get("walk_forward_score"),
        "monte_carlo_score": record.get("monte_carlo_score"),
        "drift_score": record.get("drift_score"),
        "sensitivity_score": record.get("sensitivity_score"),
        "mode": "SHADOW_RESEARCH_ONLY",
    }


def build_metric_rows(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    return [dict(metric) for metric in record.get("metrics") or ()]


def build_validation_workspace(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in records]
    statuses = Counter(str(item.get("status") or "UNKNOWN") for item in items)
    scores = [float(item["validation_score"]) for item in items if item.get("validation_score") is not None]
    stability = [float(item["stability_score"]) for item in items if item.get("stability_score") is not None]
    drift = [float(item["drift_score"]) for item in items if item.get("drift_score") is not None]
    return {
        "cards": {
            "total_validations": len(items),
            "passed": statuses.get("PASSED", 0),
            "failed": statuses.get("FAILED", 0),
            "inconclusive": statuses.get("INCONCLUSIVE", 0),
            "average_validation_score": round(mean(scores), 6) if scores else None,
            "average_stability_score": round(mean(stability), 6) if stability else None,
            "average_drift_score": round(mean(drift), 6) if drift else None,
            "mode": "SHADOW_RESEARCH_ONLY",
        },
        "status_counts": dict(sorted(statuses.items())),
        "rows": items,
    }
