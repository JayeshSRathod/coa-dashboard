"""Small, domain-free Streamlit components used by the Decision Workstation."""

from __future__ import annotations

from html import escape
from typing import Iterable


def _tone(value: str) -> str:
    normalized = value.upper()
    if normalized in {"GOOD", "READY", "FRESH", "PAPER", "ACTIVE", "QUALIFIED"}:
        return "good"
    if normalized in {"CAUTION", "BUILDING", "STALE", "WATCH", "UPCOMING"}:
        return "warn"
    if normalized in {"AVOID", "FAILED", "UNAVAILABLE", "NO_TRADE", "BLOCKED"}:
        return "bad"
    return "info"


def status_badge(label: str, value: str) -> str:
    """Return safe HTML for a compact status badge."""
    return f'<span class="cqrp-badge cqrp-{_tone(value)}">{escape(label)}: {escape(value)}</span>'


def metric_card(label: str, value: object, *, note: str = "") -> str:
    """Return a safe generic metric card; callers retain domain ownership."""
    shown_value = "—" if value is None or value == "" else str(value)
    note_html = f'<div class="cqrp-note">{escape(note)}</div>' if note else ""
    return (
        '<div class="cqrp-card">'
        f'<div class="cqrp-label">{escape(label)}</div>'
        f'<div class="cqrp-value">{escape(shown_value)}</div>{note_html}</div>'
    )


def availability_label(*, available: bool, source: str = "") -> tuple[str, str]:
    """Describe source coverage without exposing an empty provider-specific widget."""
    if available:
        return "AVAILABLE", f"Source: {source}" if source else "Available"
    return "HIDDEN", "Not shown until a reliable source is configured"


def evidence_status(*, sample_count: int, qualified_threshold: int = 100) -> tuple[str, str]:
    """Classify evidence maturity; it intentionally makes no probability claim."""
    if sample_count >= qualified_threshold:
        return "QUALIFIED", f"{sample_count} completed samples"
    if sample_count > 0:
        return "BUILDING", f"{sample_count}/{qualified_threshold} completed samples"
    return "UPCOMING", "Evidence collection has not started"


def reason_list(reasons: Iterable[object]) -> list[str]:
    """Return display-safe non-empty reasons in their original order."""
    return [str(reason) for reason in reasons if str(reason).strip()]
