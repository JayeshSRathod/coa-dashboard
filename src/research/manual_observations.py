"""Deterministic service for recording human market-review evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.persistence import RESEARCH_MIGRATIONS, apply_migrations, connect
from src.persistence.manual_observation_repository import ManualObservationRepository


EVENT_TYPES = (
    "EOS_TOUCH", "EOS_REJECTION", "EOS_BREAK", "EOR_TOUCH", "EOR_REJECTION",
    "EOR_BREAK", "SUPPORT_RESISTANCE_MIGRATION", "VOLUME_BURST",
    "OI_CONFIRMATION", "MOMENTUM_STALL", "REENTRY", "FIVE_MINUTE_CONFIRMATION",
    "CAPTURE_GAP", "OTHER",
)


@dataclass(frozen=True)
class ManualObservation:
    observed_at: str
    session_date: str
    instrument: str
    event_type: str
    narrative: str
    scenario_number: int | None = None
    scenario_name: str | None = None
    spot: float | None = None
    support: float | None = None
    resistance: float | None = None
    eos: float | None = None
    eor: float | None = None
    expected_outcome: str | None = None
    actual_outcome: str | None = None
    reference_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    observation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "operator"
    source: str = "MANUAL"

    def validate(self) -> None:
        if not self.instrument.strip():
            raise ValueError("Instrument is required.")
        if self.event_type not in EVENT_TYPES:
            raise ValueError("Unsupported observation event type.")
        if not self.narrative.strip():
            raise ValueError("Observation narrative is required.")
        if self.source != "MANUAL":
            raise ValueError("Manual observations must retain the MANUAL source.")


class ManualObservationService:
    """Creates append-only observations; it has no decision or execution authority."""

    def __init__(self, database_path: str, repository: ManualObservationRepository | None = None) -> None:
        self.connection = None
        if repository is None:
            self.connection = connect(database_path)
            apply_migrations(self.connection, RESEARCH_MIGRATIONS)
            repository = ManualObservationRepository(self.connection)
        self.repository = repository

    def record(self, observation: ManualObservation) -> str:
        observation.validate()
        return self.repository.append(asdict(observation))

    def recent(self, *, instrument: str | None = None, session_date: str | None = None,
               limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list(instrument=instrument, session_date=session_date, limit=limit)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
