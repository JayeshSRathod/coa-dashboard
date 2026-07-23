"""Single advisory Trade Decision Engine; explicitly excludes order execution."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from src.coa.canonical.models import CanonicalCOAState
from .models import DecisionEvidence, DecisionRejection, TradeDecision
from .selector import select_expiry, select_strike
DECISION_ENGINE_VERSION = "1.0.0"
class TradeDecisionEngine:
    """Combine canonical COA, validation, market quality and risk into one recommendation."""
    def decide(self, snapshot: Mapping[str, Any], coa: CanonicalCOAState, *, validation: Mapping[str, Any] | None = None, risk: Mapping[str, Any] | None = None, market_quality: str = "HEALTHY") -> TradeDecision:
        validation, risk = validation or {}, risk or {}; action = coa.recommendation; confidence = coa.confidence
        evidence = [DecisionEvidence("coa", action, coa.confidence, f"Canonical COA {coa.engine_version}", coa.engine_version), DecisionEvidence("market_quality", market_quality, None, "Market-data quality gate", "1.0")]
        rejected: list[DecisionRejection] = []
        validation_score = float(validation.get("overall_score", validation.get("score", 100)))
        if validation_score < 60: rejected.append(DecisionRejection("DECISION-VALIDATION-001", "HIGH", "Validation score is below 60.")); action = "NO_TRADE"
        if market_quality not in {"HEALTHY", "WARNING"}: rejected.append(DecisionRejection("DECISION-QUALITY-001", "HIGH", "Market data is not decision-eligible.")); action = "NO_TRADE"
        if risk.get("decision") == "REJECT" or risk.get("approved") is False: rejected.append(DecisionRejection("DECISION-RISK-001", "HIGH", str(risk.get("rejection_reason", "Risk policy rejected the recommendation.")))); action = "NO_TRADE"
        quantity = int(risk.get("approved_quantity", risk.get("quantity", 0 if action in {"NO_TRADE", "WAIT"} else 1)))
        if action not in {"BUY", "SELL"}: quantity = 0
        expiry = select_expiry(snapshot); strike, option_type = select_strike(snapshot, action); now = datetime.now(timezone.utc)
        return TradeDecision.new(snapshot_id=str(snapshot.get("snapshot_id", "")), instrument=str(snapshot.get("instrument", "")), action=action, expiry=expiry, strike=strike, option_type=option_type, entry=coa.risk.entry if action in {"BUY", "SELL"} else None, stop_loss=coa.risk.stop_loss if action in {"BUY", "SELL"} else None, target_1=coa.risk.target_1 if action in {"BUY", "SELL"} else None, target_2=coa.risk.target_2 if action in {"BUY", "SELL"} else None, quantity=quantity, confidence=round(max(0.0, min(100.0, confidence * validation_score / 100)), 2), valid_until=(now + timedelta(minutes=5)).isoformat(), status="RECOMMENDED" if action in {"BUY", "SELL"} else "REJECTED", rule_version=DECISION_ENGINE_VERSION, evidence=tuple(evidence), rejections=tuple(rejected), metadata={"execution_mode": "DISABLED", "advisory_only": True})
