"""Reproducible grid-search primitives; no automatic production changes."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class OptimizationCandidate:
    parameters: Mapping[str, Any]
    score: float


class GridSearchOptimizer:
    """Evaluate every declared parameter combination in a deterministic order."""

    def optimize(self, parameter_space: Mapping[str, Sequence[Any]], evaluator: Callable[[Mapping[str, Any]], float]) -> tuple[OptimizationCandidate, ...]:
        names = tuple(sorted(parameter_space))
        if any(not parameter_space[name] for name in names):
            raise ValueError("each optimization parameter needs at least one candidate value")
        candidates = []
        for values in product(*(parameter_space[name] for name in names)):
            parameters = dict(zip(names, values))
            candidates.append(OptimizationCandidate(parameters, float(evaluator(parameters))))
        return tuple(sorted(candidates, key=lambda item: (-item.score, tuple(repr(item.parameters[name]) for name in names))))
