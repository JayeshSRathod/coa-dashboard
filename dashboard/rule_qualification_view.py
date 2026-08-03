"""Dashboard read models for CQRP rule qualification."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable, Mapping


def build_rule_qualification_cards(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in records]
    statuses = Counter(str(item.get("status") or "UNKNOWN") for item in items)
    scores = [float(item.get("qualification_score") or 0.0) for item in items]
    return {
        "total": len(items),
        "qualified": statuses.get("QUALIFIED", 0),
        "conditional": statuses.get("CONDITIONAL", 0),
        "rejected": statuses.get("REJECTED", 0),
        "pending": statuses.get("QUALIFICATION_PENDING", 0) + statuses.get("DRAFT", 0),
        "average_score": round(mean(scores), 8) if scores else 0.0,
        "mode": "SHADOW_RULE_ONLY",
    }


def build_rule_qualification_rows(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in records:
        record = dict(item)
        rows.append({
            "qualification_id": record.get("qualification_id"),
            "rule_id": record.get("rule_id"),
            "pattern_id": record.get("pattern_id"),
            "status": record.get("status"),
            "recommendation": record.get("recommendation"),
            "qualification_score": record.get("qualification_score"),
            "validation_score": record.get("validation_score"),
            "confidence_score": record.get("confidence_score"),
            "stability_score": record.get("stability_score"),
            "sample_size": record.get("sample_size"),
            "validation_sample_size": record.get("validation_sample_size"),
            "failed_gate_count": len(record.get("failed_gates") or ()),
            "warning_count": len(record.get("warnings") or ()),
            "created_at": record.get("created_at"),
            "mode": "SHADOW_RULE_ONLY",
        })
    return rows


def build_rule_detail(record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {"status": "AWAITING_QUALIFICATION", "mode": "SHADOW_RULE_ONLY"}
    item = dict(record)
    return {
        "summary": {
            "rule_id": item.get("rule_id"),
            "status": item.get("status"),
            "recommendation": item.get("recommendation"),
            "qualification_score": item.get("qualification_score"),
            "mode": "SHADOW_RULE_ONLY",
        },
        "definition": item.get("definition") or {},
        "required_conditions": list(item.get("required_conditions") or ()),
        "failed_gates": list(item.get("failed_gates") or ()),
        "warnings": list(item.get("warnings") or ()),
        "lineage": item.get("lineage") or {},
    }
