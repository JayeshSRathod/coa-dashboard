"""Side-by-side experiment comparison over immutable run results."""

from __future__ import annotations

from typing import Iterable


def compare_runs(runs: Iterable) -> dict[str, dict]:
    result = {}
    for run in sorted(runs, key=lambda item: item.experiment_id):
        result[run.experiment_id] = dict(run.results)
    return result
