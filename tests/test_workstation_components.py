"""Tests for presentation-only Decision Workstation helpers."""

from dashboard.workstation.components import availability_label, evidence_status, metric_card, reason_list, status_badge
from dashboard.workstation.flags import workstation_enabled


def test_evidence_is_building_not_a_probability() -> None:
    assert evidence_status(sample_count=8) == ("BUILDING", "8/100 completed samples")
    assert evidence_status(sample_count=0)[0] == "UPCOMING"


def test_unavailable_provider_metric_is_hidden() -> None:
    assert availability_label(available=False) == ("HIDDEN", "Not shown until a reliable source is configured")


def test_components_escape_display_text() -> None:
    assert "&lt;script&gt;" in metric_card("<script>", "ok")
    assert "&lt;tag&gt;" in status_badge("state", "<tag>")
    assert reason_list(["first", "", "second"]) == ["first", "second"]


def test_workstation_theme_is_off_until_explicitly_enabled() -> None:
    assert workstation_enabled({}) is False
    assert workstation_enabled({"CQRP_WORKSTATION_ENABLED": "true"}) is True
