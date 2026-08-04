"""Versioned CQRP scenario catalog used for shadow research evidence.

The frozen COA structural classifier remains the source for scenarios 1--9.
The existing COA2 tactical classifier supplies its native scenarios 1--9;
CQRP records them as the non-overlapping combined IDs 10--18.  This module
does not create a signal or alter any frozen COA calculation.
"""

from __future__ import annotations

from dataclasses import dataclass


SCENARIO_CATALOG_VERSION = "combined-18-v1"


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: int
    track: str
    native_id: int
    name: str


STRUCTURAL_SCENARIOS = {
    1: "Strong range",
    2: "Slight bearish",
    3: "Slight bullish",
    4: "Extra bearish breakdown",
    5: "Extra bullish breakout",
    6: "Severe bearish",
    7: "Powerful bull run",
    8: "Gridlock / no trade",
    9: "Diverging chaos / no trade",
}


def combined_tactical_id(native_id: int) -> int:
    """Return the stable, non-overlapping CQRP ID for a COA2 state."""
    if native_id == 0:
        # Frozen COA2 uses zero for an intentionally unclassified mixed state.
        # It is evidence of uncertainty, not a mislabeled one of the 18 states.
        return 0
    if native_id not in range(1, 10):
        raise ValueError("COA2 tactical scenario must be in the range 1..9")
    return 9 + native_id


def definitions() -> tuple[ScenarioDefinition, ...]:
    """Return the deterministic 18-entry research catalog."""
    structural = tuple(
        ScenarioDefinition(scenario_id, "COA1_STRUCTURAL", scenario_id, name)
        for scenario_id, name in STRUCTURAL_SCENARIOS.items()
    )
    tactical = tuple(
        ScenarioDefinition(combined_tactical_id(native_id), "COA2_TACTICAL", native_id,
                           f"COA2 tactical state {native_id}")
        for native_id in range(1, 10)
    )
    return structural + tactical
