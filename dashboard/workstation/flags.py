"""Feature flags for staged Decision Workstation rollout."""

from __future__ import annotations

import os


def workstation_enabled(environment: dict[str, str] | None = None) -> bool:
    """Return whether the presentation theme is enabled for this process."""
    values = environment if environment is not None else os.environ
    return values.get("CQRP_WORKSTATION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
