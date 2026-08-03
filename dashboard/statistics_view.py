"""Presentation read models for CQRP statistics workspaces."""

from __future__ import annotations

from typing import Any, Mapping


def build_statistics_cards(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {
            "sample_size": 0,
            "win_rate": 0.0,
            "profit_factor": None,
            "expectancy_r": None,
            "max_drawdown": 0.0,
            "total_realized_pnl": 0.0,
            "mode": "SHADOW_PAPER_ONLY",
        }
    report = snapshot.get("report") or {}
    return {
        "statistics_id": snapshot.get("statistics_id"),
        "scope_type": snapshot.get("scope_type"),
        "scope_value": snapshot.get("scope_value"),
        "sample_size": report.get("sample_size", 0),
        "win_rate": report.get("win_rate", 0.0),
        "profit_factor": report.get("profit_factor"),
        "expectancy_r": report.get("expectancy_r"),
        "max_drawdown": report.get("max_drawdown", 0.0),
        "total_realized_pnl": report.get("total_realized_pnl", 0.0),
        "average_r_multiple": report.get("average_r_multiple"),
        "sqn": report.get("sqn"),
        "recovery_factor": report.get("recovery_factor"),
        "mode": "SHADOW_PAPER_ONLY",
    }


def build_statistics_tables(snapshot: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not snapshot:
        return {"instrument": [], "scenario": [], "horizon": [], "plan": []}
    report = snapshot.get("report") or {}

    def rows(group_name: str, label: str) -> list[dict[str, Any]]:
        group = report.get(group_name) or {}
        return [{label: key, **dict(value)} for key, value in group.items()]

    return {
        "instrument": rows("by_instrument", "instrument"),
        "scenario": rows("by_scenario", "scenario"),
        "horizon": rows("by_horizon", "planning_horizon"),
        "plan": rows("by_selected_plan", "selected_plan"),
    }
