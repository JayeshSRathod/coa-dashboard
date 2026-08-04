"""Deterministic per-snapshot COA1 plus COA2 scenario-track capture."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from engine.coa2_momentum import (
    classify_line_state,
    classify_tactical_scenario,
    compute_side_oi_change_pct,
)
from src.research.scenario_catalog import SCENARIO_CATALOG_VERSION, combined_tactical_id


class ScenarioShadowEngine:
    """Capture existing scenario tracks as append-only research evidence.

    This is a shadow observer.  It calls the already frozen COA2 classifier
    and never changes COA1, validation, signal, risk, or execution outcomes.
    """

    version = SCENARIO_CATALOG_VERSION

    def evaluate(self, snapshot: dict[str, Any], coa_result: Any,
                 history: Iterable[dict[str, Any]]) -> dict[str, Any]:
        ordered = [item for item in history if item.get("instrument") == snapshot.get("instrument")]
        ordered.sort(key=lambda item: (str(item.get("market_captured_at") or ""), str(item.get("snapshot_id") or "")))
        as_of = (str(snapshot.get("market_captured_at") or ""), str(snapshot.get("snapshot_id") or ""))
        # Historical backfills must never see a later snapshot.  The same
        # cutoff makes live capture and replay deterministic.
        ordered = [item for item in ordered if (
            str(item.get("market_captured_at") or ""), str(item.get("snapshot_id") or "")
        ) <= as_of]
        totals = [(self._total_oi(item, "Call_OI"), self._total_oi(item, "Put_OI")) for item in ordered]
        if not totals or ordered[-1].get("snapshot_id") != snapshot.get("snapshot_id"):
            totals.append((self._total_oi(snapshot, "Call_OI"), self._total_oi(snapshot, "Put_OI")))
        call_changes = [compute_side_oi_change_pct(current, previous)
                        for (previous, _), (current, _) in zip(totals, totals[1:])]
        put_changes = [compute_side_oi_change_pct(current, previous)
                       for (_, previous), (_, current) in zip(totals, totals[1:])]
        captured_at = str(snapshot.get("market_captured_at") or snapshot.get("captured_at"))
        tactical = classify_tactical_scenario(
            classify_line_state(call_changes),
            classify_line_state(put_changes),
            now=datetime.fromisoformat(captured_at.replace("Z", "+00:00")),
        )
        native_tactical_id = int(tactical["number"])
        return {
            "scenario_track_id": str(uuid4()),
            "snapshot_id": str(snapshot["snapshot_id"]),
            "session_id": str(snapshot["session_id"]),
            "instrument": str(snapshot["instrument"]),
            "coa_result_id": str(coa_result.coa_result_id),
            "structural_scenario_number": getattr(coa_result, "scenario_number", None),
            "structural_scenario": getattr(coa_result, "scenario", None),
            "tactical_scenario_number": combined_tactical_id(native_tactical_id),
            "tactical_native_number": native_tactical_id,
            "tactical_action": str(tactical.get("action") or "NO_TRADE"),
            "catalog_version": self.version,
            "payload": {
                "tactical": dict(tactical),
                "call_oi_change_history": call_changes,
                "put_oi_change_history": put_changes,
                "observation_only": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _total_oi(snapshot: dict[str, Any], key: str) -> float:
        total = 0.0
        for row in snapshot.get("option_chain") or ():
            try:
                total += float(row.get(key) or 0.0)
            except (TypeError, ValueError):
                continue
        return round(total, 6)
