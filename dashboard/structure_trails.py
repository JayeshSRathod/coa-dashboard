"""Serializable intraday structure-trail view models for CQRP Dashboard.

This module is presentation-only: it transforms append-only research evidence
into chart-ready rows and never calculates, changes, or approves COA logic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


LEVELS = ("SUPPORT", "EOS", "RESISTANCE", "EOR")
STRUCTURE_MARKERS = frozenset({
    "LEVEL_MIGRATED", "RESISTANCE_BREAK", "FALSE_BREAKOUT", "EOS_REJECTION",
    "EOS_BREAK", "RETEST", "REENTRY", "MOMENTUM_STALL", "FIVE_MINUTE_OUTCOME",
    "FIVE_MINUTE_CONFIRMATION",
})


def build_level_trail(events: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return chronological spot/level points and important chart markers."""
    points: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("event_id") or ""))):
        payload = dict(event.get("payload") or {})
        timestamp = event.get("occurred_at")
        event_type = str(event.get("event_type") or "")
        if event_type == "STRUCTURE_SNAPSHOT":
            levels = dict(payload.get("levels") or {})
            point = {"timestamp": timestamp, "spot": _number(payload.get("spot")), "scenario": event.get("scenario_track")}
            point.update({name.lower(): _number(levels.get(name)) for name in LEVELS})
            points.append(point)
        elif event_type in STRUCTURE_MARKERS:
            spot = _number(payload.get("spot"))
            if spot is not None:
                markers.append({
                    "timestamp": timestamp, "spot": spot, "event_type": event_type,
                    "detail": _marker_detail(event_type, payload),
                })
    return points, markers


def build_wall_trails(walls: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group CE/PE top-wall strike history into chart-ready trace records."""
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for wall in sorted(walls, key=lambda item: (str(item.get("captured_at") or ""), str(item.get("wall_id") or ""))):
        key = (str(wall.get("side") or ""), str(wall.get("metric") or ""), int(wall.get("rank") or 0))
        grouped[key].append({
            "timestamp": wall.get("captured_at"), "strike": _number(wall.get("strike")),
            "contract": (wall.get("payload") or {}).get("contract"), "expiry": wall.get("expiry"),
            "metric_value": _number(wall.get("metric_value")),
        })
    return [
        {"side": side, "metric": metric, "rank": rank, "label": f"{side} {metric} wall #{rank}", "points": points}
        for (side, metric, rank), points in sorted(grouped.items())
    ]


def _marker_detail(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "LEVEL_MIGRATED":
        return f"{payload.get('level')}: {payload.get('from_level')} → {payload.get('to_level')}"
    if event_type == "FIVE_MINUTE_OUTCOME":
        return f"5-minute result: {payload.get('result') or 'RECORDED'}"
    return event_type.replace("_", " ").title()


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
