"""Session-aware planning policy shared by next-session and intraday research.

The same deterministic CQRP planning engine is used for both horizons. This
policy only defines when a plan is valid, when it must be revalidated, and when
it expires. It has no broker dependency and cannot place an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class PlanningSessionPolicy:
    horizon: str
    generation_window_start: time
    generation_window_end: time
    activation_window_start: time
    activation_window_end: time
    mandatory_revalidation: bool
    maximum_plan_age_minutes: int
    force_expire_at: time
    paper_only: bool = True

    def __post_init__(self) -> None:
        if self.horizon not in {"NEXT_SESSION", "INTRADAY"}:
            raise ValueError("horizon must be NEXT_SESSION or INTRADAY")
        if self.maximum_plan_age_minutes < 1:
            raise ValueError("maximum_plan_age_minutes must be positive")
        if not self.paper_only:
            raise ValueError("current CQRP planning policies must remain PAPER-only")

    def can_generate(self, observed_at: datetime) -> bool:
        local = observed_at.astimezone(IST).time().replace(tzinfo=None)
        return self.generation_window_start <= local <= self.generation_window_end

    def can_activate(self, observed_at: datetime) -> bool:
        local = observed_at.astimezone(IST).time().replace(tzinfo=None)
        return self.activation_window_start <= local <= self.activation_window_end

    def is_expired(self, created_at: datetime, observed_at: datetime) -> bool:
        created = created_at.astimezone(IST)
        observed = observed_at.astimezone(IST)
        if observed.date() != created.date() and self.horizon == "INTRADAY":
            return True
        if observed.time().replace(tzinfo=None) >= self.force_expire_at:
            return True
        age_minutes = (observed - created).total_seconds() / 60.0
        return age_minutes > self.maximum_plan_age_minutes


NEXT_SESSION_POLICY = PlanningSessionPolicy(
    horizon="NEXT_SESSION",
    generation_window_start=time(15, 10),
    generation_window_end=time(15, 35),
    activation_window_start=time(9, 0),
    activation_window_end=time(10, 0),
    mandatory_revalidation=True,
    maximum_plan_age_minutes=18 * 60,
    force_expire_at=time(15, 30),
)


INTRADAY_POLICY = PlanningSessionPolicy(
    horizon="INTRADAY",
    generation_window_start=time(9, 15),
    generation_window_end=time(15, 15),
    activation_window_start=time(9, 15),
    activation_window_end=time(15, 15),
    mandatory_revalidation=True,
    maximum_plan_age_minutes=30,
    force_expire_at=time(15, 20),
)


def policy_for(horizon: str) -> PlanningSessionPolicy:
    normalized = str(horizon).upper()
    if normalized == "NEXT_SESSION":
        return NEXT_SESSION_POLICY
    if normalized == "INTRADAY":
        return INTRADAY_POLICY
    raise ValueError(f"unsupported planning horizon: {horizon}")
