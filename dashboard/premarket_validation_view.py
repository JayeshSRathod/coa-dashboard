"""Presentation-only read model for CQRP plan revalidation results."""

from __future__ import annotations

from typing import Any, Mapping


def build_validation_cards(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return stable dashboard cards without business logic or broker authority."""
    if not record:
        return {
            "status": "AWAITING_VALIDATION",
            "selected_plan": None,
            "opening_classification": None,
            "confidence_before": None,
            "confidence_after": None,
            "confidence_delta": None,
            "mode": "SHADOW_PAPER_ONLY",
        }
    before = float(record.get("confidence_before") or 0.0)
    after = float(record.get("confidence_after") or 0.0)
    return {
        "validation_id": record.get("validation_id"),
        "trade_plan_id": record.get("trade_plan_id"),
        "status": record.get("validation_result"),
        "selected_plan": record.get("selected_plan"),
        "opening_classification": record.get("opening_classification"),
        "planning_horizon": record.get("planning_horizon"),
        "confidence_before": before,
        "confidence_after": after,
        "confidence_delta": round(after - before, 4),
        "risk_status": record.get("risk_status"),
        "data_quality": record.get("data_quality"),
        "mode": "SHADOW_PAPER_ONLY",
    }


def build_validation_rows(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    rows: list[dict[str, Any]] = []
    for reason in record.get("reasons") or ():
        rows.append({"type": "REASON", "message": str(reason)})
    for warning in record.get("warnings") or ():
        rows.append({"type": "WARNING", "message": str(warning)})
    evidence = record.get("evidence") or {}
    for key in sorted(evidence):
        rows.append({"type": "EVIDENCE", "message": key, "value": evidence[key]})
    return rows
