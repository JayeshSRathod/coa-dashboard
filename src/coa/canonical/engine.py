"""Coordinator for additive canonical COA; frozen mathematics remains untouched."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Mapping
from engine.coa2_momentum import classify_line_state, classify_tactical_scenario, compute_side_oi_change_pct
from ..adapter import FrozenCOAAdapter
from .compatibility import evaluate as compatibility_evaluate
from .models import CanonicalCOAState, COAEvidence, RiskPlan, StructuralState, TacticalState
from .versions import CANONICAL_COA_VERSION, RULE_REGISTRY
def _number(value: Any) -> float:
    try: return float(value or 0)
    except (TypeError, ValueError): return 0.0
class CanonicalCOAEngine:
    """One deterministic and explainable facade over documented COA v1/v2 rules."""
    engine_version = f"COA-Canonical-{CANONICAL_COA_VERSION}"
    def __init__(self, frozen_adapter: FrozenCOAAdapter | None = None) -> None: self._frozen = frozen_adapter or FrozenCOAAdapter()
    def analyze(self, snapshot: Mapping[str, Any], *, experiment_id: str | None = None) -> CanonicalCOAState:
        legacy = self._frozen.analyze(snapshot, experiment_id=experiment_id); raw = legacy.raw_output
        support_bias, resistance_bias = raw.get("support_bias", "STABLE"), raw.get("resistance_bias", "STABLE")
        direction = "BULLISH" if support_bias == "BULLISH" and resistance_bias != "BEARISH" else "BEARISH" if resistance_bias == "BEARISH" and support_bias != "BULLISH" else "NEUTRAL"
        strength = min(100.0, max(0.0, (2.0 - _number(raw.get("support_ratio")) - _number(raw.get("resistance_ratio"))) * 50))
        structural = StructuralState(legacy.scenario_number, legacy.scenario, direction, legacy.support, legacy.resistance, _number(raw.get("support_ratio")), _number(raw.get("resistance_ratio")), {"support": support_bias, "resistance": resistance_bias}, {"support": str(raw.get("support_state")), "resistance": str(raw.get("resistance_state"))}, legacy.eos, legacy.eor, strength, legacy.risk_mode)
        chain, metadata = snapshot.get("option_chain") or [], snapshot.get("metadata") or {}
        call_oi = sum(_number(r.get("Call_OI", r.get("CE_OI"))) for r in chain); put_oi = sum(_number(r.get("Put_OI", r.get("PE_OI"))) for r in chain)
        call_history = list(metadata.get("call_oi_change_history", [compute_side_oi_change_pct(call_oi, _number(metadata.get("previous_call_oi")))])); put_history = list(metadata.get("put_oi_change_history", [compute_side_oi_change_pct(put_oi, _number(metadata.get("previous_put_oi")))]))
        tactical_raw = classify_tactical_scenario(classify_line_state(call_history), classify_line_state(put_history)); action = str(tactical_raw["action"])
        bias = "BULLISH" if action.startswith("BUY") else "BEARISH" if action in {"SELL", "SHORT", "SELL_RALLIES"} else "NEUTRAL"
        tactical = TacticalState(int(tactical_raw["number"]), str(tactical_raw["name"]), bias, action, str(tactical_raw["dynamics"]), "PUT" if bias == "BULLISH" else "CALL" if bias == "BEARISH" else "NEUTRAL", "UNAVAILABLE", "INTRADAY", 75.0 if bias != "NEUTRAL" else 50.0, action)
        compatibility = compatibility_evaluate(structural, tactical); entry = structural.eos if compatibility.decision == "BUY" else structural.eor if compatibility.decision == "SELL" else None; span = abs((structural.eor or 0) - (structural.eos or 0))
        risk = RiskPlan(entry, entry - span*.25 if entry and compatibility.decision == "BUY" else entry + span*.25 if entry else None, entry + span*.5 if entry and compatibility.decision == "BUY" else entry - span*.5 if entry else None, structural.eor if compatibility.decision == "BUY" else structural.eos if compatibility.decision == "SELL" else None, "15:20 Asia/Kolkata", "1.0")
        stamp = str(snapshot.get("market_captured_at") or snapshot.get("captured_at") or datetime.now(timezone.utc).isoformat()); evidence = tuple(COAEvidence(rule.rule_id, rule.version, "APPLIED", 1.0, rule.description, stamp) for rule in RULE_REGISTRY)
        return CanonicalCOAState(str(snapshot.get("snapshot_id", "")), str(snapshot.get("session_id", "")), self.engine_version, structural, tactical, compatibility, risk, evidence, compatibility.warnings)
