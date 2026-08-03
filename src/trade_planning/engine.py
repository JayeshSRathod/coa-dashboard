"""Deterministic next-session trade planning from existing CQRP evidence.

The planner is PAPER/research only. It does not fetch external data, place an
order, change risk, or promote a rule. It converts the latest approved CQRP
snapshot, signal, validation, technical state, and risk outcome into a
preliminary next-session plan with three opening contingencies.
"""

from __future__ import annotations

from .models import OpeningPlan, TradePlan, TradePlanningInput


_BULLISH_SCENARIOS = frozenset({3, 5, 7})
_BEARISH_SCENARIOS = frozenset({2, 4, 6})
_NEUTRAL_SCENARIOS = frozenset({1})
_BLOCKED_SCENARIOS = frozenset({8, 9})


class TradePlanningEngine:
    """Create one explainable, preliminary next-session PAPER plan."""

    version = "trade-planner-v1"

    def plan(self, item: TradePlanningInput) -> TradePlan:
        market_bias = self._market_bias(item)
        expected_opening = self._expected_opening(item, market_bias)
        readiness, warnings = self._readiness(item, market_bias)
        confidence = self._confidence(item, market_bias, readiness)
        direction = item.direction if readiness in {"READY", "CONDITIONAL"} else None
        option_type = "CE" if direction == "BUY" else "PE" if direction == "SELL" else None
        rationale = self._rationale(item, market_bias, expected_opening)
        opening_plans = self._opening_plans(item, market_bias, direction, readiness)

        return TradePlan.new(
            snapshot_id=item.snapshot_id,
            signal_id=item.signal_id,
            risk_decision_id=item.risk_decision_id,
            instrument=item.instrument,
            expiry=item.expiry,
            market_bias=market_bias,
            expected_opening=expected_opening,
            direction=direction,
            option_type=option_type,
            entry=item.entry if direction else None,
            stop_loss=item.stop_loss if direction else None,
            target_1=item.target_1 if direction else None,
            target_2=item.target_2 if direction else None,
            confidence_score=confidence,
            readiness=readiness,
            status="PRELIMINARY",
            valid_for_session=None,
            rationale=rationale,
            warnings=warnings,
            opening_plans=opening_plans,
            evidence={
                "scenario_number": item.scenario_number,
                "scenario": item.scenario,
                "risk_mode": item.risk_mode,
                "support": item.support,
                "resistance": item.resistance,
                "eos": item.eos,
                "eor": item.eor,
                "technical_status": item.technical_status,
                "technical_bias": item.technical_bias,
                "momentum_state": item.momentum_state,
                "validation_passed": item.validation_passed,
                **dict(item.evidence),
            },
            planner_version=self.version,
        )

    @staticmethod
    def _market_bias(item: TradePlanningInput) -> str:
        if item.risk_mode == "HALT_TRADING" or item.scenario_number in _BLOCKED_SCENARIOS:
            return "UNCERTAIN"
        if item.scenario_number in _BULLISH_SCENARIOS:
            return "BULLISH"
        if item.scenario_number in _BEARISH_SCENARIOS:
            return "BEARISH"
        if item.scenario_number in _NEUTRAL_SCENARIOS:
            return "NEUTRAL"
        if item.direction == "BUY":
            return "BULLISH"
        if item.direction == "SELL":
            return "BEARISH"
        return "UNCERTAIN"

    @staticmethod
    def _expected_opening(item: TradePlanningInput, market_bias: str) -> str:
        """Return a preliminary structural expectation, never a certainty."""
        if market_bias == "BULLISH":
            if item.eor is not None and item.spot > item.eor:
                return "GAP_UP"
            return "FLAT"
        if market_bias == "BEARISH":
            if item.eos is not None and item.spot < item.eos:
                return "GAP_DOWN"
            return "FLAT"
        if market_bias == "NEUTRAL":
            return "FLAT"
        return "UNCERTAIN"

    @staticmethod
    def _readiness(item: TradePlanningInput, market_bias: str) -> tuple[str, tuple[str, ...]]:
        warnings: list[str] = [
            "Preliminary next-session plan; pre-open revalidation is mandatory.",
            "This record is PAPER/research only and cannot submit a broker order.",
        ]
        if item.risk_mode == "HALT_TRADING" or item.scenario_number in _BLOCKED_SCENARIOS:
            warnings.append("COA structure is a no-trade or conflict state.")
            return "BLOCKED", tuple(warnings)
        if not item.validation_passed:
            warnings.append("Validation did not pass.")
            return "OBSERVE_ONLY", tuple(warnings)
        if item.signal_type not in {"BUY", "SELL"} or item.direction not in {"BUY", "SELL"}:
            warnings.append("No directional research signal is available.")
            return "OBSERVE_ONLY", tuple(warnings)
        if None in {item.entry, item.stop_loss, item.target_1, item.target_2}:
            warnings.append("One or more required trade levels are missing.")
            return "OBSERVE_ONLY", tuple(warnings)
        if market_bias == "BULLISH" and item.direction != "BUY":
            warnings.append("Directional signal conflicts with bullish COA structure.")
            return "OBSERVE_ONLY", tuple(warnings)
        if market_bias == "BEARISH" and item.direction != "SELL":
            warnings.append("Directional signal conflicts with bearish COA structure.")
            return "OBSERVE_ONLY", tuple(warnings)
        technical = str(item.technical_status or "").upper()
        technical_bias = str(item.technical_bias or "").upper()
        if technical in {"FAILED", "REJECTED", "CONFLICT"}:
            warnings.append("Technical confirmation is conflicting or failed.")
            return "OBSERVE_ONLY", tuple(warnings)
        if technical_bias and technical_bias not in {market_bias, "NEUTRAL", "MIXED"}:
            warnings.append("Technical bias is not aligned with COA structure.")
            return "CONDITIONAL", tuple(warnings)
        if item.confidence_score < 70:
            warnings.append("Confidence is below the ready-plan threshold.")
            return "CONDITIONAL", tuple(warnings)
        return "READY", tuple(warnings)

    @staticmethod
    def _confidence(item: TradePlanningInput, market_bias: str, readiness: str) -> float:
        score = float(item.confidence_score)
        if item.validation_passed:
            score += 5.0
        if str(item.technical_status or "").upper() in {"CONFIRMED", "PASS", "ALIGNED"}:
            score += 5.0
        if str(item.technical_bias or "").upper() == market_bias:
            score += 5.0
        if str(item.momentum_state or "").upper() in {"BULLISH", "BEARISH", "CONFIRMED", "STRONG"}:
            score += 3.0
        if readiness == "CONDITIONAL":
            score -= 10.0
        elif readiness == "OBSERVE_ONLY":
            score = min(score, 49.0)
        elif readiness == "BLOCKED":
            score = 0.0
        return round(max(0.0, min(score, 100.0)), 4)

    @staticmethod
    def _rationale(item: TradePlanningInput, market_bias: str, expected_opening: str) -> tuple[str, ...]:
        reasons = [
            f"COA structural bias is {market_bias}.",
            f"Preliminary opening classification is {expected_opening}.",
        ]
        if item.scenario_number is not None:
            reasons.append(f"Closing COA scenario is {item.scenario_number}: {item.scenario or 'unnamed scenario'}.")
        if item.validation_passed:
            reasons.append("The latest persisted validation passed.")
        if item.technical_status:
            reasons.append(f"Technical confirmation status is {item.technical_status}.")
        if item.momentum_state:
            reasons.append(f"Closing momentum state is {item.momentum_state}.")
        if item.eor is not None and item.spot > item.eor:
            reasons.append("Spot closed above EOR.")
        if item.eos is not None and item.spot < item.eos:
            reasons.append("Spot closed below EOS.")
        return tuple(reasons)

    @staticmethod
    def _opening_plans(item: TradePlanningInput, market_bias: str,
                       direction: str | None, readiness: str) -> tuple[OpeningPlan, ...]:
        if readiness in {"BLOCKED", "OBSERVE_ONLY"} or direction is None:
            common = "Do not activate a paper trade until a fresh pre-open and opening validation passes."
            return (
                OpeningPlan("A", "Expected opening occurs", "WAIT", common, "Remain unvalidated", ("Observe only",)),
                OpeningPlan("B", "Opening is flat", "WAIT", common, "Remain unvalidated", ("Observe only",)),
                OpeningPlan("C", "Opening opposes the closing structure", "CANCEL", common, "Contrary opening", ("Preserve evidence",)),
            )

        action = "PAPER_BUY_CE" if direction == "BUY" else "PAPER_BUY_PE"
        expected = "Gap up or bullish hold" if market_bias == "BULLISH" else "Gap down or bearish hold"
        adverse = "Gap down" if market_bias == "BULLISH" else "Gap up"
        favourable_level = item.eor if direction == "BUY" else item.eos
        defence_level = item.support if direction == "BUY" else item.resistance
        entry_text = f"Revalidate structure, then use planned entry {item.entry}."
        if favourable_level is not None:
            entry_text += f" Confirm behaviour around {favourable_level}."
        invalidation = f"Cancel if structure fails around {defence_level}." if defence_level is not None else "Cancel if validation or risk fails."
        return (
            OpeningPlan("A", expected, action, entry_text, invalidation,
                        ("Do not chase an extended opening.", "Require fresh COA/technical confirmation.")),
            OpeningPlan("B", "Flat opening inside the closing range", action,
                        entry_text, invalidation,
                        ("Wait for opening-range confirmation.", "Use the existing PAPER lifecycle only.")),
            OpeningPlan("C", adverse, "WAIT_OR_CANCEL",
                        "Do not use the closing plan automatically; rebuild from the first valid opening structure.",
                        "Cancel if the adverse gap breaks the closing defence level.",
                        ("No averaging", "No automatic reversal")),
        )
