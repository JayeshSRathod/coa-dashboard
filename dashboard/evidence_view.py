"""Presentation read models for the CQRP evidence workspace."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def build_evidence_cards(record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {
            "status": "NO_EVIDENCE",
            "outcome": None,
            "realized_pnl": 0.0,
            "realized_r_multiple": None,
            "mfe": 0.0,
            "mae": 0.0,
            "mode": "SHADOW_PAPER_ONLY",
        }
    return {
        "evidence_id": record.get("evidence_id"),
        "trade_id": record.get("trade_id"),
        "instrument": record.get("instrument"),
        "planning_horizon": record.get("planning_horizon"),
        "scenario_number": record.get("scenario_number"),
        "scenario": record.get("scenario"),
        "outcome": record.get("outcome"),
        "realized_pnl": float(record.get("realized_pnl") or 0.0),
        "realized_r_multiple": record.get("realized_r_multiple"),
        "mfe": float(record.get("mfe") or 0.0),
        "mae": float(record.get("mae") or 0.0),
        "holding_seconds": record.get("holding_seconds"),
        "confidence_score": record.get("confidence_score"),
        "selected_plan": record.get("selected_plan"),
        "mode": "SHADOW_PAPER_ONLY",
    }


def build_evidence_rows(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    rows: list[dict[str, Any]] = []
    for key, value in sorted((record.get("feature_vector") or {}).items()):
        rows.append({"section": "FEATURE", "field": key, "value": value})
    for key, value in sorted((record.get("lineage") or {}).items()):
        rows.append({"section": "LINEAGE", "field": key, "value": value})
    return rows


def build_evidence_workspace(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in records]
    outcomes = Counter(str(item.get("outcome") or "UNKNOWN") for item in items)
    instruments = Counter(str(item.get("instrument") or "UNKNOWN") for item in items)
    total_pnl = sum(float(item.get("realized_pnl") or 0.0) for item in items)
    r_values = [float(item["realized_r_multiple"]) for item in items if item.get("realized_r_multiple") is not None]
    return {
        "cards": {
            "total_records": len(items),
            "wins": outcomes.get("WIN", 0),
            "losses": outcomes.get("LOSS", 0),
            "breakeven": outcomes.get("BREAKEVEN", 0),
            "cancelled": outcomes.get("CANCELLED", 0),
            "expired": outcomes.get("EXPIRED", 0),
            "total_realized_pnl": round(total_pnl, 8),
            "average_r_multiple": round(sum(r_values) / len(r_values), 8) if r_values else None,
            "mode": "SHADOW_PAPER_ONLY",
        },
        "outcome_counts": dict(sorted(outcomes.items())),
        "instrument_counts": dict(sorted(instruments.items())),
        "rows": items,
    }
