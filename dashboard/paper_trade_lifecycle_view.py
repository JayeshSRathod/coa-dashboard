"""Presentation read models for CQRP PAPER trade lifecycle workspaces."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def build_trade_cards(detail: Mapping[str, Any] | None) -> dict[str, Any]:
    if not detail:
        return {
            "status": "NOT_FOUND",
            "stage": None,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "realized_r_multiple": None,
            "mfe": 0.0,
            "mae": 0.0,
            "holding_seconds": None,
            "mode": "PAPER_ONLY",
        }
    summary = detail.get("summary") or {}
    trade = detail.get("trade") or {}
    return {
        "trade_id": trade.get("trade_id"),
        "instrument": trade.get("instrument"),
        "direction": trade.get("direction"),
        "status": summary.get("status"),
        "stage": summary.get("stage"),
        "quantity": summary.get("quantity"),
        "quantity_remaining": summary.get("quantity_remaining"),
        "entry_price": summary.get("entry_price"),
        "average_exit_price": summary.get("average_exit_price"),
        "realized_pnl": summary.get("realized_pnl", 0.0),
        "unrealized_pnl": summary.get("unrealized_pnl", 0.0),
        "realized_r_multiple": summary.get("realized_r_multiple"),
        "mfe": summary.get("mfe", 0.0),
        "mae": summary.get("mae", 0.0),
        "holding_seconds": summary.get("holding_seconds"),
        "exit_reason": summary.get("exit_reason"),
        "mode": "PAPER_ONLY",
    }


def build_timeline_rows(detail: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not detail:
        return []
    rows: list[dict[str, Any]] = []
    for event in detail.get("timeline") or ():
        payload = event.get("payload") or {}
        rows.append({
            "occurred_at": event.get("occurred_at"),
            "event_type": event.get("event_type"),
            "source_snapshot_id": event.get("source_snapshot_id"),
            "price": payload.get("price"),
            "quantity": payload.get("quantity"),
            "reason": payload.get("reason"),
            "payload": dict(payload),
        })
    return rows


def build_session_workspace(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(row) for row in rows]
    stages = Counter(str(row.get("stage") or "UNKNOWN") for row in items)
    realized = sum(float(row.get("realized_pnl") or 0.0) for row in items)
    unrealized = sum(float(row.get("unrealized_pnl") or 0.0) for row in items)
    winners = sum(1 for row in items if float(row.get("realized_pnl") or 0.0) > 0)
    losers = sum(1 for row in items if float(row.get("realized_pnl") or 0.0) < 0)
    return {
        "cards": {
            "total_trades": len(items),
            "active": stages.get("ACTIVE", 0) + stages.get("TP1", 0) + stages.get("TRAILING", 0),
            "waiting": stages.get("WAITING", 0),
            "closed": stages.get("EXITED", 0),
            "cancelled": stages.get("CANCELLED", 0),
            "realized_pnl": round(realized, 6),
            "unrealized_pnl": round(unrealized, 6),
            "winners": winners,
            "losers": losers,
            "mode": "PAPER_ONLY",
        },
        "stage_counts": dict(sorted(stages.items())),
        "rows": items,
    }
