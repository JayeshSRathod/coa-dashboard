"""Option-chain completeness and strike-spacing assessment."""

from __future__ import annotations

from collections.abc import Mapping

from src.coa.models import COAResearchResult

from ._chain import number, rows, selected_strike
from .models import ComponentAssessment


class StrikeQualityValidator:
    name = "strike_quality"

    def assess(self, snapshot: Mapping[str, object], coa_result: COAResearchResult) -> ComponentAssessment:
        chain = rows(snapshot)
        strikes = sorted({value for row in chain if (value := number(row, ("Strike", "strike"))) is not None and value > 0})
        if len(strikes) < 2:
            return ComponentAssessment.new(
                name=self.name, score=0, failures=("fewer than two valid strikes are available",),
                details={"valid_strikes": len(strikes)},
            )
        spacing = [right - left for left, right in zip(strikes, strikes[1:])]
        spacing_ok = min(spacing) > 0 and max(spacing) - min(spacing) < 1e-8
        spot = snapshot.get("spot")
        try:
            spot = float(spot)
        except (TypeError, ValueError):
            spot = None
        selected = selected_strike(snapshot, coa_result.raw_output)
        nearest = min(strikes, key=lambda strike: abs(strike - spot)) if spot is not None else None
        atm_available = nearest in strikes if nearest is not None else False
        completeness = snapshot.get("data_completeness")
        try:
            completeness = float(completeness) if completeness is not None else 1.0
        except (TypeError, ValueError):
            completeness = 0.0
        score = 45 * max(0, min(1, completeness)) + (30 if spacing_ok else 0) + (25 if atm_available else 0)
        warnings = []
        if not spacing_ok:
            warnings.append("strike spacing is inconsistent")
        if selected is None:
            warnings.append("selected strike is unavailable; distance-from-spot is not assessed")
        else:
            score += 5 if selected in strikes else -15
            if selected not in strikes:
                warnings.append("selected strike is not present in the option-chain sample")
        return ComponentAssessment.new(
            name=self.name, score=max(0, min(100, score)),
            reasons=("option-chain strikes are usable",),
            warnings=warnings,
            details={"valid_strikes": len(strikes), "spacing": spacing[0], "spacing_consistent": spacing_ok,
                     "atm_strike": nearest, "selected_strike": selected, "completeness": completeness},
        )
