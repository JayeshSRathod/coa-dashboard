"""Deterministic backtest coordinator for an injected CQRP research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Iterable, Mapping

from .metrics import performance_metrics


def _fingerprint(value: object) -> str:
    return sha256(json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class BacktestResult:
    input_fingerprint: str
    trade_pnls: tuple[float, ...]
    metrics: Mapping[str, float | int]


class BacktestRunner:
    """Runs an injected historical pipeline once per snapshot in chronological order.

    The callback is intentionally injected so research reuses the approved CQRP
    scanner/COA/decision/paper-execution path instead of reimplementing rules.
    It may return a number, a mapping containing ``pnl``, or ``None``.
    """

    def run(self, snapshots: Iterable[Mapping[str, Any]], pipeline: Callable[[Mapping[str, Any]], Any]) -> BacktestResult:
        ordered = tuple(sorted((dict(snapshot) for snapshot in snapshots), key=lambda item: (item.get("market_captured_at", item.get("captured_at", "")), item.get("snapshot_id", ""))))
        pnls: list[float] = []
        for snapshot in ordered:
            output = pipeline(snapshot)
            if output is None:
                continue
            value = output.get("pnl") if isinstance(output, Mapping) else output
            if value is not None:
                pnls.append(float(value))
        fingerprint = _fingerprint({"snapshots": ordered, "pnls": pnls})
        return BacktestResult(fingerprint, tuple(pnls), performance_metrics(pnls))
