"""Serializable, presentation-only read models for the CQRP workstation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def option_activity_rows(ladder: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Produce chart-ready strike activity rows; no ranking or trading decision occurs here."""
    rows: list[dict[str, Any]] = []
    for row in ladder:
        strike = _number(row.get("strike"))
        if strike is None:
            continue
        rows.append({
            "strike": strike,
            "is_atm": bool(row.get("is_atm")),
            "ce_oi": _number(row.get("ce_oi")) or 0.0,
            "pe_oi": _number(row.get("pe_oi")) or 0.0,
            "ce_volume": _number(row.get("ce_volume")) or 0.0,
            "pe_volume": _number(row.get("pe_volume")) or 0.0,
            "ce_oi_change": _number(row.get("ce_oi_change")) or 0.0,
            "pe_oi_change": _number(row.get("pe_oi_change")) or 0.0,
        })
    return rows


def index_comparison(feed: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize already-produced decision-feed rows for comparable display only."""
    rows = []
    for item in feed:
        confidence = _number(item.get("confidence"))
        rows.append({
            "instrument": str(item.get("instrument") or ""),
            "score": confidence,
            "signal": item.get("signal") or "NO_DATA",
            "scenario": item.get("scenario"),
            "market_state": item.get("market_state") or "UNKNOWN",
            "technical": item.get("technical") or "UNKNOWN",
            "updated_at": item.get("updated_at"),
            "rank": None,
        })
    eligible = sorted((row for row in rows if row["score"] is not None), key=lambda row: (-float(row["score"]), row["instrument"]))
    for rank, row in enumerate(eligible, start=1):
        row["rank"] = rank
    return sorted(rows, key=lambda row: (row["rank"] is None, row["rank"] or 999, row["instrument"]))


def conditional_plan(plan: Mapping[str, Any] | None) -> dict[str, Any]:
    """Expose only advisory plan fields, always retaining next-open revalidation."""
    if not plan:
        return {
            "state": "NO_PLAN",
            "headline": "No plan until CQRP pre-close gates pass.",
            "activation": "A valid next-session plan is created only in the 15:00–15:20 IST capture window.",
            "invalidation": "No plan is actionable before next-open validation.",
            "opening_plans": [],
        }
    return {
        "state": str(plan.get("status") or "PRELIMINARY"),
        "headline": f"{plan.get('readiness') or 'CONDITIONAL'} — {plan.get('expected_opening') or 'UNCERTAIN'}",
        "activation": "Revalidate on the first valid FYERS snapshot after open.",
        "invalidation": "Cancel or switch when pre-market validation fails.",
        "instrument": plan.get("instrument"),
        "expiry": plan.get("expiry"),
        "direction": plan.get("direction"),
        "option_type": plan.get("option_type"),
        "entry": plan.get("entry"),
        "stop_loss": plan.get("stop_loss"),
        "target_1": plan.get("target_1"),
        "target_2": plan.get("target_2"),
        "confidence_score": plan.get("confidence_score"),
        "opening_plans": list(plan.get("opening_plans") or []),
        "rationale": list(plan.get("rationale") or []),
        "warnings": list(plan.get("warnings") or []),
    }


def scenario_evidence(track: Mapping[str, Any] | None) -> dict[str, Any]:
    """Present observational 18-scenario data without claiming predictive maturity."""
    if not track:
        return {"status": "UPCOMING", "label": "18-scenario shadow evidence", "detail": "Awaiting captured scenario tracks."}
    return {
        "status": "BUILDING",
        "label": "18-scenario shadow evidence",
        "detail": "Observational capture only; not a qualified predictive rule.",
        "structural": track.get("structural_scenario_number"),
        "tactical": track.get("tactical_scenario_number"),
        "catalog_version": track.get("catalog_version"),
    }


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
