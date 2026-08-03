"""Deterministic CQRP pre-market and intraday plan revalidation.

The engine compares a persisted PAPER TradePlan with a fresh market observation.
It does not call a broker, create an order, or modify the source TradePlan.
"""

from __future__ import annotations

from src.trade_planning.models import TradePlan

from .models import PreMarketObservation, PreMarketValidationResult


class PreMarketValidationEngine:
    """Validate, modify, cancel, or observe a planned trade using fresh evidence."""

    version = "premarket-validator-v1"
    gap_threshold_pct = 0.20
    adverse_gap_cancel_pct = 0.60

    def validate(
        self,
        plan: TradePlan,
        observation: PreMarketObservation,
    ) -> PreMarketValidationResult:
        self._assert_identity(plan, observation)

        opening = self._opening_classification(observation.gap_pct)
        reasons: list[str] = []
        warnings: list[str] = [
            "PAPER/shadow validation only; no broker order is permitted.",
        ]

        hard_failure = self._hard_failure(plan, observation, warnings)
        selected_plan = self._select_plan(plan, observation, opening)
        confidence = self._adjust_confidence(plan, observation, opening, selected_plan)

        if hard_failure is not None:
            result = "CANCELLED"
            selected_plan = "C"
            confidence = 0.0
            reasons.append(hard_failure)
        elif plan.readiness in {"BLOCKED", "OBSERVE_ONLY"}:
            result = "OBSERVE_ONLY"
            selected_plan = None
            confidence = min(confidence, 49.0)
            reasons.append(f"Source plan readiness is {plan.readiness}.")
        elif selected_plan == "C":
            result = "CANCELLED"
            confidence = min(confidence, 25.0)
            reasons.append("Fresh market structure opposes the planned direction.")
        elif selected_plan == "B":
            result = "MODIFIED"
            reasons.append("Opening structure is usable only with renewed confirmation.")
        else:
            result = "VALIDATED"
            reasons.append("Fresh market structure confirms the planned direction.")

        reasons.extend(self._explain(plan, observation, opening, selected_plan))

        return PreMarketValidationResult.new(
            trade_plan_id=plan.trade_plan_id,
            source_snapshot_id=plan.snapshot_id,
            observed_snapshot_id=observation.snapshot_id,
            planning_horizon=plan.planning_horizon,
            validation_result=result,
            selected_plan=selected_plan,
            opening_classification=opening,
            confidence_before=plan.confidence_score,
            confidence_after=confidence,
            risk_status=observation.risk_status,
            data_quality=observation.data_quality,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            evidence={
                "instrument": plan.instrument,
                "plan_market_bias": plan.market_bias,
                "observed_coa_bias": observation.coa_bias,
                "technical_status": observation.technical_status,
                "technical_bias": observation.technical_bias,
                "momentum_state": observation.momentum_state,
                "gap_pct": observation.gap_pct,
                "gift_nifty_change_pct": observation.gift_nifty_change_pct,
                "global_score": observation.global_score,
                "news_risk": observation.news_risk,
                **dict(observation.metadata),
            },
            validator_version=self.version,
        )

    @staticmethod
    def _assert_identity(plan: TradePlan, observation: PreMarketObservation) -> None:
        if observation.trade_plan_id != plan.trade_plan_id:
            raise ValueError("observation trade_plan_id does not match plan")
        if observation.instrument != plan.instrument:
            raise ValueError("observation instrument does not match plan")
        if observation.planning_horizon != plan.planning_horizon:
            raise ValueError("observation planning_horizon does not match plan")

    def _opening_classification(self, gap_pct: float) -> str:
        if gap_pct >= self.gap_threshold_pct:
            return "GAP_UP"
        if gap_pct <= -self.gap_threshold_pct:
            return "GAP_DOWN"
        return "FLAT"

    @staticmethod
    def _hard_failure(
        plan: TradePlan,
        observation: PreMarketObservation,
        warnings: list[str],
    ) -> str | None:
        if plan.status in {"CANCELLED", "EXPIRED"}:
            return f"Source plan status is {plan.status}."
        if str(observation.data_quality).upper() not in {"PASS", "HEALTHY"}:
            return "Fresh market data quality failed."
        if str(observation.risk_status).upper() not in {"PASS", "APPROVED", "REDUCED_SIZE"}:
            return "Fresh risk validation failed."
        if str(observation.news_risk).upper() in {"HIGH", "BLOCK", "HALT"}:
            return "Overnight or session news risk is blocking activation."
        if str(observation.technical_status or "").upper() in {"FAILED", "REJECTED", "CONFLICT"}:
            return "Technical confirmation failed."
        if plan.direction is None:
            return "Source plan has no executable direction."
        if None in {plan.entry, plan.stop_loss, plan.target_1, plan.target_2}:
            warnings.append("One or more source trade levels are missing.")
            return "Source trade plan is incomplete."
        return None

    def _select_plan(
        self,
        plan: TradePlan,
        observation: PreMarketObservation,
        opening: str,
    ) -> str | None:
        bullish_plan = plan.direction == "BUY"
        observed_bias = str(observation.coa_bias).upper()
        technical_bias = str(observation.technical_bias or "").upper()

        adverse_gap = (
            bullish_plan and observation.gap_pct <= -self.adverse_gap_cancel_pct
        ) or (
            not bullish_plan and observation.gap_pct >= self.adverse_gap_cancel_pct
        )
        if adverse_gap:
            return "C"

        bias_conflict = (
            bullish_plan and observed_bias == "BEARISH"
        ) or (
            not bullish_plan and observed_bias == "BULLISH"
        )
        technical_conflict = (
            bullish_plan and technical_bias == "BEARISH"
        ) or (
            not bullish_plan and technical_bias == "BULLISH"
        )
        if bias_conflict or technical_conflict:
            return "C"

        expected = (
            bullish_plan and opening == "GAP_UP"
        ) or (
            not bullish_plan and opening == "GAP_DOWN"
        )
        aligned_bias = (
            bullish_plan and observed_bias == "BULLISH"
        ) or (
            not bullish_plan and observed_bias == "BEARISH"
        )
        if expected and aligned_bias:
            return "A"
        return "B"

    @staticmethod
    def _adjust_confidence(
        plan: TradePlan,
        observation: PreMarketObservation,
        opening: str,
        selected_plan: str | None,
    ) -> float:
        score = float(plan.confidence_score)
        observed_bias = str(observation.coa_bias).upper()
        technical_status = str(observation.technical_status or "").upper()
        technical_bias = str(observation.technical_bias or "").upper()
        momentum = str(observation.momentum_state or "").upper()

        aligned = (
            plan.direction == "BUY" and observed_bias == "BULLISH"
        ) or (
            plan.direction == "SELL" and observed_bias == "BEARISH"
        )
        if aligned:
            score += 8.0
        else:
            score -= 12.0
        if technical_status in {"CONFIRMED", "PASS", "ALIGNED"}:
            score += 5.0
        if technical_bias == observed_bias and technical_bias in {"BULLISH", "BEARISH"}:
            score += 4.0
        if momentum in {"STRONG", "CONFIRMED", "BULLISH", "BEARISH"}:
            score += 3.0
        if selected_plan == "A":
            score += 5.0
        elif selected_plan == "B":
            score -= 5.0
        elif selected_plan == "C":
            score -= 35.0
        if opening == "FLAT":
            score -= 2.0
        if str(observation.risk_status).upper() == "REDUCED_SIZE":
            score -= 5.0
        return round(max(0.0, min(score, 100.0)), 4)

    @staticmethod
    def _explain(
        plan: TradePlan,
        observation: PreMarketObservation,
        opening: str,
        selected_plan: str | None,
    ) -> list[str]:
        reasons = [
            f"Observed opening classification is {opening} ({observation.gap_pct:.2f}%).",
            f"Observed COA bias is {observation.coa_bias}.",
            f"Selected contingency plan is {selected_plan or 'NONE'}.",
        ]
        if observation.technical_status:
            reasons.append(f"Technical status is {observation.technical_status}.")
        if observation.momentum_state:
            reasons.append(f"Momentum state is {observation.momentum_state}.")
        if plan.planning_horizon == "INTRADAY":
            reasons.append("Result is valid only for the current intraday policy window.")
        else:
            reasons.append("Result is a next-session revalidation of the closing plan.")
        return reasons
