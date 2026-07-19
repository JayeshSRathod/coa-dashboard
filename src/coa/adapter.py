"""Adapter that isolates CQRP research callers from the frozen COA v1 math."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

import pandas as pd

from engine.coa_math import analyze_coa_matrix_structure
from engine.instruments import INSTRUMENTS
from src.common.version import COA_ENGINE_VERSION

from .models import COAResearchResult


class SnapshotTranslationError(ValueError):
    """Raised when a persisted snapshot cannot be represented as COA v1 input."""


_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "Strike": ("Strike", "strike"),
    "Call_Vol": ("Call_Vol", "CE_Vol", "call_volume"),
    "Put_Vol": ("Put_Vol", "PE_Vol", "put_volume"),
    "Call_LTP": ("Call_LTP", "CE_LTP", "call_ltp"),
    "Put_LTP": ("Put_LTP", "PE_LTP", "put_ltp"),
}


def _number(value: Any, field: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotTranslationError(f"option_chain row {row_number} has invalid {field}") from exc
    if number < 0 or (field == "Strike" and number <= 0):
        raise SnapshotTranslationError(f"option_chain row {row_number} has invalid {field}")
    return number


def _value(row: Mapping[str, Any], field: str, row_number: int) -> float:
    for candidate in _REQUIRED_COLUMNS[field]:
        if candidate in row and row[candidate] is not None:
            return _number(row[candidate], field, row_number)
    raise SnapshotTranslationError(f"option_chain row {row_number} is missing {field}")


def _infer_step(strikes: list[float]) -> int | float:
    ordered = sorted(set(strikes))
    differences = [right - left for left, right in zip(ordered, ordered[1:]) if right > left]
    if not differences:
        raise SnapshotTranslationError("cannot infer COA step from fewer than two strikes")
    step = min(differences)
    if step <= 0 or any(abs((difference / step) - round(difference / step)) > 1e-8 for difference in differences):
        raise SnapshotTranslationError("option-chain strikes do not have a consistent COA step")
    return int(step) if step.is_integer() else step


def _step_size(snapshot: Mapping[str, Any], strikes: list[float]) -> int | float:
    metadata = snapshot.get("metadata") or {}
    configured = metadata.get("step_size") if isinstance(metadata, Mapping) else None
    if configured is not None:
        return _number(configured, "step_size", 0)
    instrument = snapshot.get("instrument")
    if instrument in INSTRUMENTS:
        return INSTRUMENTS[instrument]["step_size"]
    return _infer_step(strikes)


def _optional_float(raw: Mapping[str, Any], key: str) -> float | None:
    value = raw.get(key)
    return float(value) if value is not None else None


class FrozenCOAAdapter:
    """Translate snapshot records to COA v1 inputs and return typed outputs.

    This class invokes only the frozen structural COA function. Momentum and
    diversion require state across snapshots, so they remain explicitly None.
    """

    engine_version = COA_ENGINE_VERSION
    strategy_version = "COA Core v1.0"

    def analyze(
        self,
        snapshot: Mapping[str, Any],
        *,
        experiment_id: str | None = None,
    ) -> COAResearchResult:
        started = perf_counter()
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        session_id = str(snapshot.get("session_id") or "")
        market_timestamp = str(snapshot.get("market_captured_at") or snapshot.get("captured_at") or "")
        if not snapshot_id or not session_id or not market_timestamp:
            raise SnapshotTranslationError("snapshot_id, session_id, and market timestamp are required")
        try:
            spot = float(snapshot["spot"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SnapshotTranslationError("snapshot spot must be a valid number") from exc
        if spot <= 0:
            raise SnapshotTranslationError("snapshot spot must be positive")
        chain = snapshot.get("option_chain")
        if not isinstance(chain, list) or not chain:
            raise SnapshotTranslationError("snapshot option_chain must contain at least one row")

        rows: list[dict[str, float]] = []
        for index, source_row in enumerate(chain):
            if not isinstance(source_row, Mapping):
                raise SnapshotTranslationError(f"option_chain row {index} is not an object")
            rows.append({field: _value(source_row, field, index) for field in _REQUIRED_COLUMNS})
        frame = pd.DataFrame(rows, columns=list(_REQUIRED_COLUMNS))
        step = _step_size(snapshot, frame["Strike"].tolist())
        raw = analyze_coa_matrix_structure(frame, spot, step)

        metadata = snapshot.get("metadata") or {}
        strategy_version = (
            metadata.get("strategy_version", self.strategy_version)
            if isinstance(metadata, Mapping) else self.strategy_version
        )
        return COAResearchResult.new(
            snapshot_id=snapshot_id,
            session_id=session_id,
            experiment_id=experiment_id,
            strategy_version=str(strategy_version),
            engine_version=self.engine_version,
            scenario_number=raw.get("scenario_number"),
            scenario=raw.get("scenario"),
            eos=_optional_float(raw, "eos"),
            eor=_optional_float(raw, "eor"),
            support=_optional_float(raw, "support"),
            resistance=_optional_float(raw, "resistance"),
            momentum=None,
            diversion=None,
            trend=None,
            direction=None,
            risk_mode=raw.get("risk_mode"),
            raw_output=raw,
            processing_time_ms=(perf_counter() - started) * 1000,
            market_timestamp=market_timestamp,
            created_by=type(self).__name__,
        )
