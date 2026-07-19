"""Configuration boundary for deterministic research signal rules."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class SignalConfig:
    minimum_confidence: float = 65.0
    minimum_volume_score: float = 50.0
    minimum_oi_score: float = 60.0
    minimum_liquidity_score: float = 50.0
    scenario_directions: Mapping[int, str] = field(
        default_factory=lambda: {5: "BUY", 4: "SELL"}
    )
    signal_version: str = "1.0.0"

    def __post_init__(self) -> None:
        for name in ("minimum_confidence", "minimum_volume_score",
                     "minimum_oi_score", "minimum_liquidity_score"):
            value = float(getattr(self, name))
            if not 0 <= value <= 100:
                raise ValueError(name + " must be between 0 and 100")
        normalised = {int(key): str(value).upper() for key, value in self.scenario_directions.items()}
        if any(value not in {"BUY", "SELL"} for value in normalised.values()):
            raise ValueError("scenario directions may only be BUY or SELL")
        object.__setattr__(self, "scenario_directions", normalised)

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "SignalConfig":
        payload = dict(values)
        directions = payload.pop("scenario_directions", payload.pop("allowed_scenarios", {}))
        if isinstance(directions, list):
            directions = {item: "BUY" for item in directions}
        payload["scenario_directions"] = directions or {5: "BUY", 4: "SELL"}
        return cls(**payload)

    @classmethod
    def from_file(cls, path: Path | str) -> "SignalConfig":
        """Load JSON configuration without introducing a runtime YAML dependency."""
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_mapping(json.load(handle))

    def direction_for(self, scenario_number: int | None) -> str | None:
        return self.scenario_directions.get(scenario_number) if scenario_number is not None else None
