"""Deterministic option liquidity and tradability evidence assessment."""

from __future__ import annotations

from collections.abc import Mapping

from src.coa.models import COAResearchResult

from ._chain import number, rows, selected_strike
from .models import ComponentAssessment


class LiquidityValidator:
    name = "liquidity"

    def assess(self, snapshot: Mapping[str, object], coa_result: COAResearchResult) -> ComponentAssessment:
        chain = rows(snapshot)
        selected = selected_strike(snapshot, coa_result.raw_output)
        candidate = None
        if selected is not None:
            candidate = next(
                (row for row in chain if number(row, ("Strike", "strike")) == float(selected)), None
            )
        if candidate is None and chain:
            candidate = chain[0]
        if candidate is None:
            return ComponentAssessment.new(
                name=self.name, score=0, failures=("no option-chain row is available for liquidity assessment",)
            )
        call_ltp = number(candidate, ("Call_LTP", "CE_LTP", "call_ltp"))
        put_ltp = number(candidate, ("Put_LTP", "PE_LTP", "put_ltp"))
        if call_ltp is None or put_ltp is None or call_ltp <= 0 or put_ltp <= 0:
            return ComponentAssessment.new(
                name=self.name, score=0, failures=("selected strike has missing or non-positive option prices",),
                details={"selected_strike": selected},
            )
        volumes = [number(candidate, ("Call_Vol", "CE_Vol", "call_volume")),
                   number(candidate, ("Put_Vol", "PE_Vol", "put_volume"))]
        oi = [number(candidate, ("Call_OI", "CE_OI", "call_oi")),
              number(candidate, ("Put_OI", "PE_OI", "put_oi"))]
        score = 45
        warnings = []
        score += 25 if all(value is not None and value > 0 for value in volumes) else 0
        if not all(value is not None and value > 0 for value in volumes):
            warnings.append("selected strike has limited volume evidence")
        score += 20 if all(value is not None and value > 0 for value in oi) else 0
        if not all(value is not None and value > 0 for value in oi):
            warnings.append("selected strike has limited OI evidence")
        bid = number(candidate, ("Call_Bid", "CE_Bid", "bid"))
        ask = number(candidate, ("Call_Ask", "CE_Ask", "ask"))
        if bid is not None and ask is not None and bid > 0 and ask >= bid:
            midpoint = (bid + ask) / 2
            spread_pct = ((ask - bid) / midpoint * 100) if midpoint else 100
            score += 10 if spread_pct <= 2 else 0
            if spread_pct > 2:
                warnings.append("selected strike bid/ask spread is wide")
        else:
            warnings.append("bid/ask spread is unavailable")
        return ComponentAssessment.new(
            name=self.name, score=max(0, min(100, score)),
            reasons=("selected strike has positive call and put prices",),
            warnings=warnings,
            details={"selected_strike": selected, "call_ltp": call_ltp, "put_ltp": put_ltp},
        )
