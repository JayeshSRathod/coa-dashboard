"""UI-independent chronological replay of stored market snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.persistence.snapshot_repository import SnapshotRepository


@dataclass
class ReplayService:
    repository: SnapshotRepository
    snapshots: list[dict[str, Any]]
    playback_speed: float = 1.0
    _position: int = -1

    @classmethod
    def for_session(cls, repository: SnapshotRepository, session_id: str) -> "ReplayService":
        return cls(repository=repository, snapshots=repository.list_by_session(session_id))

    @classmethod
    def for_time_range(
        cls,
        repository: SnapshotRepository,
        instrument: str,
        start: str,
        end: str,
    ) -> "ReplayService":
        return cls(repository=repository, snapshots=repository.list_by_time_range(instrument, start, end))

    @property
    def current(self) -> dict[str, Any] | None:
        if 0 <= self._position < len(self.snapshots):
            return self.snapshots[self._position]
        return None

    @property
    def position(self) -> int:
        return self._position

    def set_playback_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError("playback speed must be positive")
        self.playback_speed = speed

    def reset(self) -> None:
        self._position = -1

    def step_forward(self, steps: int = 1) -> dict[str, Any] | None:
        if steps < 1:
            raise ValueError("steps must be at least one")
        if not self.snapshots:
            return None
        self._position = min(self._position + steps, len(self.snapshots) - 1)
        return self.current

    def step_backward(self, steps: int = 1) -> dict[str, Any] | None:
        if steps < 1:
            raise ValueError("steps must be at least one")
        if not self.snapshots:
            return None
        self._position = max(self._position - steps, 0)
        return self.current
