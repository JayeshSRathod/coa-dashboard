"""Presentation read models for the CQRP execution-intelligence workspace."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


def build_execution_cards(record: Mapping[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {
            "status": "AWAITING_DECISION",
            "policy_allowed": None,
            "execution_eligible": None,
            "action": None,
            "paper_trade_id": None,
            "mode": "SHADOW_PAPER_ONLY",
        }
    return {
        "audit_id": record.get("audit_id"),
        "trade_plan_id": record.get("trade_plan_id"),
        "instrument": record.get("instrument"),
        "planning_horizon": record.get("planning_horizon"),
        "policy_allowed": bool(record.get("policy_allowed")),
        "execution_eligible": bool(record.get("execution_eligible")),
        "action": record.get("action"),
        "paper_trade_id": record.get("paper_trade_id"),
        "created_at": record.get("created_at"),
        "mode": "SHADOW_PAPER_ONLY",
    }


def build_execution_reason_rows(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    rows: list[dict[str, Any]] = []
    for reason in record.get("reasons") or ():
        rows.append({"type": "REASON", "message": str(reason)})
    evidence = record.get("evidence") or {}
    for key in sorted(evidence):
        rows.append({"type": "EVIDENCE", "field": key, "value": evidence[key]})
    return rows


def build_execution_workspace(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in records]
    actions = Counter(str(item.get("action") or "UNKNOWN") for item in items)
    instruments = Counter(str(item.get("instrument") or "UNKNOWN") for item in items)
    allowed = sum(1 for item in items if bool(item.get("policy_allowed")))
    eligible = sum(1 for item in items if bool(item.get("execution_eligible")))
    executed = actions.get("PAPER_TRADE_PERSISTED", 0)
    blocked = actions.get("BLOCK_PAPER_EXECUTION", 0) + actions.get("DO_NOT_EXECUTE", 0)
    return {
        "cards": {
            "total_decisions": len(items),
            "policy_allowed": allowed,
            "execution_eligible": eligible,
            "paper_trades_persisted": executed,
            "blocked": blocked,
            "mode": "SHADOW_PAPER_ONLY",
        },
        "action_counts": dict(sorted(actions.items())),
        "instrument_counts": dict(sorted(instruments.items())),
        "rows": items,
    }
