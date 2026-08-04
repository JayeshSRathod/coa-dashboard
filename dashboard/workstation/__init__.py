"""CQRP Decision Workstation presentation components.

This package is deliberately presentation-only. It converts already-computed
CQRP read models into concise operator-facing widgets and never calculates a
trading decision or writes to a repository.
"""

from .components import availability_label, evidence_status, metric_card, reason_list, status_badge
from .flags import workstation_enabled
from .read_models import conditional_plan, index_comparison, option_activity_rows, scenario_evidence
from .theme import apply_workstation_theme

__all__ = [
    "apply_workstation_theme",
    "availability_label",
    "evidence_status",
    "metric_card",
    "reason_list",
    "status_badge",
    "workstation_enabled",
    "conditional_plan",
    "index_comparison",
    "option_activity_rows",
    "scenario_evidence",
]
