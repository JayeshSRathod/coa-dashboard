"""Deterministic open-interest evidence assessment; never a standalone trigger."""

from __future__ import annotations

from collections.abc import Mapping

from src.coa.models import COAResearchResult

from ._chain import number, rows
from .models import ComponentAssessment


class OpenInterestValidator:
    name = "open_interest"

    def assess(self, snapshot: Mapping[str, object], coa_result: COAResearchResult) -> ComponentAssessment:
        chain = rows(snapshot)
        calls = [number(row, ("Call_OI", "CE_OI", "call_oi")) for row in chain]
        puts = [number(row, ("Put_OI", "PE_OI", "put_oi")) for row in chain]
        calls = [value for value in calls if value is not None and value >= 0]
        puts = [value for value in puts if value is not None and value >= 0]
        if not chain or not calls or not puts:
            return ComponentAssessment.new(
                name=self.name, score=0,
                failures=("open-interest data is unavailable for one or both option sides",),
                details={"rows": len(chain), "call_points": len(calls), "put_points": len(puts)},
            )
        coverage = (len(calls) + len(puts)) / (2 * len(chain))
        total_call, total_put = sum(calls), sum(puts)
        concentration = max(max(calls), max(puts)) / max(total_call + total_put, 1)
        score = 50 * coverage + 30 * min(concentration * 4, 1) + 20
        warnings = []
        has_change = any(
            number(row, ("Call_OI_Change", "CE_OI_Change", "Put_OI_Change", "PE_OI_Change"))
            is not None for row in chain
        )
        if not has_change:
            warnings.append("OI-change data is unavailable; build-up or unwinding is not assessed")
        if coa_result.direction is None:
            warnings.append("COA direction is unavailable; directional OI alignment is not assessed")
        return ComponentAssessment.new(
            name=self.name, score=max(0, min(100, score)),
            reasons=("call and put open interest are present",),
            warnings=warnings,
            details={"coverage": coverage, "call_total": total_call, "put_total": total_put,
                     "concentration": concentration},
        )
