"""Market-window helpers for research scheduling; no strategy calculations."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")
PRECLOSE_START = time(15, 0)
PRECLOSE_END = time(15, 20)


def is_preclose_window(timestamp: str) -> bool:
    """Whether a captured market timestamp falls in the configured plan window."""
    value = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(IST).time()
    return PRECLOSE_START <= value <= PRECLOSE_END
