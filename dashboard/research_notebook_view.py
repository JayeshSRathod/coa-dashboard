"""Presentation read models for the CQRP Research Notebook workspace."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def build_experiment_cards(detail: Mapping[str, Any] | None) -> dict[str, Any]:
    if not detail:
        return {
            "status": "NOT_FOUND",
            "runs": 0,
            "observations": 0,
            "conclusions": 0,
            "mode": "SHADOW_RESEARCH_ONLY",
        }
    experiment = detail.get("experiment") or {}
    return {
        "experiment_id": experiment.get("experiment_id"),
        "title": experiment.get("title"),
        "status": experiment.get("status"),
        "primary_metric": experiment.get("primary_metric"),
        "minimum_sample_size": experiment.get("minimum_sample_size"),
        "runs": len(detail.get("runs") or ()),
        "observations": len(detail.get("observations") or ()),
        "conclusions": len(detail.get("conclusions") or ()),
        "owner": experiment.get("owner"),
        "mode": "SHADOW_RESEARCH_ONLY",
    }


def build_experiment_timeline(detail: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not detail:
        return []
    rows: list[dict[str, Any]] = []
    for run in detail.get("runs") or ():
        rows.append({
            "type": "RUN",
            "timestamp": run.get("started_at"),
            "status": run.get("status"),
            "reference_id": run.get("run_id"),
            "summary": f"Evidence count: {run.get('evidence_count', 0)}",
        })
    for observation in detail.get("observations") or ():
        rows.append({
            "type": "OBSERVATION",
            "timestamp": observation.get("created_at"),
            "status": observation.get("observation_type"),
            "reference_id": observation.get("observation_id"),
            "summary": observation.get("title") or observation.get("body"),
        })
    for conclusion in detail.get("conclusions") or ():
        rows.append({
            "type": "CONCLUSION",
            "timestamp": conclusion.get("created_at"),
            "status": conclusion.get("conclusion"),
            "reference_id": conclusion.get("conclusion_id"),
            "summary": conclusion.get("summary"),
        })
    return sorted(rows, key=lambda row: (str(row.get("timestamp") or ""), str(row.get("reference_id") or "")), reverse=True)


def build_notebook_workspace(experiments: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in experiments]
    statuses = Counter(str(item.get("status") or "UNKNOWN") for item in items)
    return {
        "cards": {
            "total_experiments": len(items),
            "draft": statuses.get("DRAFT", 0),
            "running": statuses.get("RUNNING", 0),
            "completed": statuses.get("COMPLETED", 0),
            "rejected": statuses.get("REJECTED", 0),
            "promoted": statuses.get("PROMOTED", 0),
            "archived": statuses.get("ARCHIVED", 0),
            "mode": "SHADOW_RESEARCH_ONLY",
        },
        "status_counts": dict(sorted(statuses.items())),
        "rows": items,
    }
