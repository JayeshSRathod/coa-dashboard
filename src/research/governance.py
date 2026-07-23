"""Strategy promotion lifecycle.  Promotion remains explicitly human approved."""

from __future__ import annotations


LIFECYCLE = ("DRAFT", "TESTING", "VALIDATED", "APPROVED", "PRODUCTION", "RETIRED")
_TRANSITIONS = {
    "DRAFT": {"TESTING", "RETIRED"},
    "TESTING": {"VALIDATED", "RETIRED"},
    "VALIDATED": {"APPROVED", "RETIRED"},
    "APPROVED": {"PRODUCTION", "RETIRED"},
    "PRODUCTION": {"RETIRED"},
    "RETIRED": set(),
}


def validate_transition(current: str, target: str, *, approved_by: str | None = None) -> str:
    """Validate a lifecycle transition without persisting or auto-promoting anything."""
    if current not in _TRANSITIONS or target not in _TRANSITIONS:
        raise ValueError("unknown strategy lifecycle state")
    if target not in _TRANSITIONS[current]:
        raise ValueError(f"invalid lifecycle transition: {current} -> {target}")
    if target in {"APPROVED", "PRODUCTION"} and not approved_by:
        raise ValueError("human approver is required for approval or production")
    return target
