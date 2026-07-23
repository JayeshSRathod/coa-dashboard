"""Immutable public contracts for canonical COA analysis."""
from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
def _freeze(value: Mapping[str, Any]) -> Mapping[str, Any]: return MappingProxyType(dict(value))
@dataclass(frozen=True)
class RuleVersion: rule_id: str; version: str; description: str
@dataclass(frozen=True)
class StructuralState:
    scenario_id: int | None; scenario: str | None; direction: str; support: float | None; resistance: float | None; support_strength: float | None; resistance_strength: float | None; dominance: Mapping[str, str]; vector: Mapping[str, str]; eos: float | None; eor: float | None; confidence: float; risk_mode: str | None
    def __post_init__(self) -> None:
        object.__setattr__(self, "dominance", _freeze(self.dominance)); object.__setattr__(self, "vector", _freeze(self.vector))
@dataclass(frozen=True)
class TacticalState:
    scenario_id: int; scenario: str; market_bias: str; momentum: str; pressure: str; oi_bias: str; premium_bias: str; market_phase: str; confidence: float; action: str
@dataclass(frozen=True)
class CompatibilityResult:
    decision: str; confidence_modifier: float; priority: str; required_validations: tuple[str, ...]; warnings: tuple[str, ...] = ()
@dataclass(frozen=True)
class COAEvidence:
    rule_id: str; rule_version: str; result: str; weight: float; comment: str; timestamp: str
@dataclass(frozen=True)
class RiskPlan:
    entry: float | None; stop_loss: float | None; target_1: float | None; target_2: float | None; time_exit: str; rule_version: str
@dataclass(frozen=True)
class CanonicalCOAState:
    snapshot_id: str; session_id: str; engine_version: str; structural: StructuralState; tactical: TacticalState; compatibility: CompatibilityResult; risk: RiskPlan; evidence: tuple[COAEvidence, ...] = field(default_factory=tuple); warnings: tuple[str, ...] = field(default_factory=tuple)
    @property
    def recommendation(self) -> str: return self.compatibility.decision
    @property
    def confidence(self) -> float: return round(max(0.0, min(100.0, self.structural.confidence * self.tactical.confidence / 100 + self.compatibility.confidence_modifier)), 2)
