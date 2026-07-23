"""Walk-forward validation helpers that keep in-sample and out-of-sample windows separate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class WalkForwardWindow:
    training: tuple[Mapping[str, Any], ...]
    validation: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class WalkForwardResult:
    windows: tuple[WalkForwardWindow, ...]
    validation_scores: tuple[float, ...]
    passed: bool


class WalkForwardValidator:
    def split(self, observations: Iterable[Mapping[str, Any]], *, training_size: int, validation_size: int, step_size: int | None = None) -> tuple[WalkForwardWindow, ...]:
        rows = tuple(observations)
        if training_size < 1 or validation_size < 1:
            raise ValueError("training_size and validation_size must be positive")
        step = step_size or validation_size
        if step < 1:
            raise ValueError("step_size must be positive")
        windows = []
        for start in range(0, len(rows) - training_size - validation_size + 1, step):
            split = start + training_size
            windows.append(WalkForwardWindow(rows[start:split], rows[split:split + validation_size]))
        return tuple(windows)

    def evaluate(self, observations: Iterable[Mapping[str, Any]], *, training_size: int, validation_size: int, evaluator: Callable[[tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]], float], minimum_score: float = 0.0) -> WalkForwardResult:
        windows = self.split(observations, training_size=training_size, validation_size=validation_size)
        scores = tuple(float(evaluator(window.training, window.validation)) for window in windows)
        return WalkForwardResult(windows, scores, bool(scores) and min(scores) >= minimum_score)
