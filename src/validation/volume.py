"""Deterministic option-volume evidence assessment."""

from __future__ import annotations

from collections.abc import Mapping

from src.coa.models import COAResearchResult

from ._chain import number, rows
from .models import ComponentAssessment


class VolumeValidator:
    name = "volume"

    def assess(self, snapshot: Mapping[str, object], coa_result: COAResearchResult) -> ComponentAssessment:
        chain = rows(snapshot)
        call_values = [number(row, ("Call_Vol", "CE_Vol", "call_volume")) for row in chain]
        put_values = [number(row, ("Put_Vol", "PE_Vol", "put_volume")) for row in chain]
        call = [value for value in call_values if value is not None and value >= 0]
        put = [value for value in put_values if value is not None and value >= 0]
        if not chain or not call or not put:
            return ComponentAssessment.new(
                name=self.name, score=0,
                failures=("volume data is unavailable for one or both option sides",),
                details={"rows": len(chain), "call_points": len(call), "put_points": len(put)},
            )
        coverage = (len(call) + len(put)) / (2 * len(chain))
        call_total, put_total = sum(call), sum(put)
        balance = min(call_total, put_total) / max(call_total, put_total) if max(call_total, put_total) else 0
        score = 50 * coverage + 30 * balance + 20
        warnings = []
        metadata = snapshot.get("metadata") or {}
        baseline = metadata.get("volume_baseline") if isinstance(metadata, Mapping) else None
        if baseline is None:
            warnings.append("recent volume baseline is unavailable")
        else:
            try:
                expansion = (call_total + put_total) / float(baseline)
                score += 10 if expansion >= 1 else -10
            except (TypeError, ValueError, ZeroDivisionError):
                warnings.append("recent volume baseline is invalid")
        if coa_result.direction is None:
            warnings.append("COA direction is unavailable; directional volume confirmation is not assessed")
        return ComponentAssessment.new(
            name=self.name, score=max(0, min(100, score)),
            reasons=("call and put volume are present",),
            warnings=warnings,
            details={"coverage": coverage, "call_total": call_total, "put_total": put_total, "balance": balance},
        )
