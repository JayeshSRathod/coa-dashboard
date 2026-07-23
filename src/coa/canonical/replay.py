"""Deterministic canonical-vs-frozen COA comparison."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .engine import CanonicalCOAEngine
@dataclass(frozen=True)
class ReplayComparison: snapshot_id: str; matches_legacy: bool; differences: Mapping[str, tuple[Any, Any]]
class COAReplayValidator:
    def __init__(self, engine: CanonicalCOAEngine | None = None) -> None: self.engine = engine or CanonicalCOAEngine()
    def compare(self, snapshot: Mapping[str, Any]) -> ReplayComparison:
        state, frozen = self.engine.analyze(snapshot), self.engine._frozen.analyze(snapshot)
        pairs = {"scenario_number": (frozen.scenario_number, state.structural.scenario_id), "eos": (frozen.eos, state.structural.eos), "eor": (frozen.eor, state.structural.eor), "support": (frozen.support, state.structural.support), "resistance": (frozen.resistance, state.structural.resistance)}; differences = {key: value for key, value in pairs.items() if value[0] != value[1]}
        return ReplayComparison(str(snapshot.get("snapshot_id", "")), not differences, differences)
