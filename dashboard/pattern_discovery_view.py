"""Presentation read models for the CQRP Pattern Discovery workspace."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def build_pattern_cards(record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {
            "status": "NOT_FOUND",
            "confidence_score": None,
            "stability_score": None,
            "support_rate": None,
            "uplift": None,
            "mode": "SHADOW_RESEARCH_ONLY",
        }
    return {
        "pattern_id": record.get("pattern_id"),
        "title": record.get("title"),
        "status": record.get("status"),
        "direction": record.get("direction"),
        "discovery_method": record.get("discovery_method"),
        "sample_size": record.get("sample_size"),
        "comparison_sample_size": record.get("comparison_sample_size"),
        "support_rate": record.get("support_rate"),
        "baseline_rate": record.get("baseline_rate"),
        "uplift": record.get("uplift"),
        "average_r_multiple": record.get("average_r_multiple"),
        "expectancy_r": record.get("expectancy_r"),
        "confidence_score": record.get("confidence_score"),
        "stability_score": record.get("stability_score"),
        "mode": "SHADOW_RESEARCH_ONLY",
    }


def build_pattern_detail_rows(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    rows: list[dict[str, Any]] = []
    definition = record.get("definition") or {}
    for key, value in sorted((definition.get("feature_conditions") or {}).items()):
        rows.append({"type": "FEATURE_CONDITION", "field": key, "value": value})
    for key, value in sorted((definition.get("comparison_group") or {}).items()):
        rows.append({"type": "COMPARISON_GROUP", "field": key, "value": value})
    for key, value in sorted((record.get("supporting_metrics") or {}).items()):
        rows.append({"type": "SUPPORTING_METRIC", "field": key, "value": value})
    for warning in record.get("warnings") or ():
        rows.append({"type": "WARNING", "message": str(warning)})
    return rows


def build_pattern_workspace(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in records]
    statuses = Counter(str(item.get("status") or "UNKNOWN") for item in items)
    directions = Counter(str(item.get("direction") or "UNKNOWN") for item in items)
    methods = Counter(str(item.get("discovery_method") or "UNKNOWN") for item in items)
    ranked = sorted(
        items,
        key=lambda item: (
            float(item.get("confidence_score") or 0.0),
            float(item.get("stability_score") or 0.0),
            int(item.get("sample_size") or 0),
        ),
        reverse=True,
    )
    return {
        "cards": {
            "total_patterns": len(items),
            "discovered": statuses.get("DISCOVERED", 0),
            "review_pending": statuses.get("REVIEW_PENDING", 0),
            "validation_pending": statuses.get("VALIDATION_PENDING", 0),
            "promoted": statuses.get("PROMOTED", 0),
            "rejected": statuses.get("REJECTED", 0),
            "mode": "SHADOW_RESEARCH_ONLY",
        },
        "status_counts": dict(sorted(statuses.items())),
        "direction_counts": dict(sorted(directions.items())),
        "method_counts": dict(sorted(methods.items())),
        "top_patterns": ranked[:20],
        "rows": items,
    }
