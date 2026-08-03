"""Deterministic pattern discovery over immutable CQRP evidence records.

The engine performs transparent group-comparison scans across categorical and
boolean evidence features. It produces research candidates only; it never
creates executable rules or broker instructions.
"""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping

from .models import PatternCandidate, PatternDefinition


class PatternDiscoveryEngine:
    version = "pattern-discovery-v1"

    def __init__(
        self,
        *,
        minimum_sample_size: int = 20,
        minimum_uplift_points: float = 8.0,
        minimum_confidence_score: float = 55.0,
    ) -> None:
        if minimum_sample_size < 2:
            raise ValueError("minimum_sample_size must be at least 2")
        self.minimum_sample_size = int(minimum_sample_size)
        self.minimum_uplift_points = float(minimum_uplift_points)
        self.minimum_confidence_score = float(minimum_confidence_score)

    def discover(
        self,
        evidence_records: Iterable[Mapping[str, Any]],
        *,
        experiment_id: str | None = None,
        source_run_id: str | None = None,
        statistics_snapshot_id: str | None = None,
        feature_keys: tuple[str, ...] | None = None,
    ) -> tuple[PatternCandidate, ...]:
        rows = [dict(record) for record in evidence_records]
        settled = [row for row in rows if str(row.get("outcome") or "").upper() in {"WIN", "LOSS", "BREAKEVEN"}]
        if len(settled) < self.minimum_sample_size:
            return ()

        baseline_rate = self._win_rate(settled)
        keys = feature_keys or self._discoverable_keys(settled)
        candidates: list[PatternCandidate] = []

        for key in keys:
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            raw_values: dict[str, Any] = {}
            for row in settled:
                value = self._feature_value(row, key)
                if value is None or isinstance(value, (dict, list, tuple, set)):
                    continue
                bucket = str(value)
                buckets[bucket].append(row)
                raw_values[bucket] = value

            for bucket, members in buckets.items():
                if len(members) < self.minimum_sample_size:
                    continue
                comparison = [row for row in settled if row not in members]
                support_rate = self._win_rate(members)
                comparison_rate = self._win_rate(comparison) if comparison else baseline_rate
                uplift = support_rate - comparison_rate
                if abs(uplift) < self.minimum_uplift_points:
                    continue

                r_values = [float(row["realized_r_multiple"]) for row in members if row.get("realized_r_multiple") is not None]
                confidence = self._confidence_score(
                    sample_size=len(members),
                    population_size=len(settled),
                    uplift=abs(uplift),
                    r_values=r_values,
                )
                if confidence < self.minimum_confidence_score:
                    continue

                stability = self._stability_score(members)
                direction = "POSITIVE" if uplift > 0 else "NEGATIVE"
                warnings: list[str] = []
                if len(comparison) < self.minimum_sample_size:
                    warnings.append("Comparison sample is below the preferred minimum.")
                if stability < 50.0:
                    warnings.append("Pattern stability is weak across evidence segments.")

                value = raw_values[bucket]
                definition = PatternDefinition.new(
                    feature_conditions={key: value},
                    outcome_target="WIN",
                    comparison_group={key: {"operator": "NOT_EQUALS", "value": value}},
                    planning_horizons=tuple(sorted({str(row.get("planning_horizon")) for row in members if row.get("planning_horizon")})),
                    instruments=tuple(sorted({str(row.get("instrument")) for row in members if row.get("instrument")})),
                    scenarios=tuple(sorted({str(row.get("scenario")) for row in members if row.get("scenario")})),
                    regimes=tuple(sorted({str(row.get("regime")) for row in members if row.get("regime")})),
                )
                evidence_ids = tuple(str(row.get("evidence_id")) for row in members if row.get("evidence_id"))
                average_r = mean(r_values) if r_values else None
                candidates.append(
                    PatternCandidate.new(
                        experiment_id=experiment_id,
                        source_run_id=source_run_id,
                        statistics_snapshot_id=statistics_snapshot_id,
                        title=f"{key} = {value}",
                        description=(
                            f"Evidence where {key} equals {value} shows a {uplift:.2f} percentage-point "
                            f"change in win rate versus the comparison group."
                        ),
                        status="DISCOVERED",
                        discovery_method="GROUP_COMPARISON",
                        direction=direction,
                        definition=definition,
                        sample_size=len(members),
                        comparison_sample_size=len(comparison),
                        support_rate=support_rate,
                        baseline_rate=comparison_rate,
                        uplift=round(uplift, 8),
                        average_r_multiple=round(average_r, 8) if average_r is not None else None,
                        expectancy_r=round(average_r, 8) if average_r is not None else None,
                        confidence_score=confidence,
                        stability_score=stability,
                        evidence_ids=evidence_ids,
                        supporting_metrics={
                            "population_sample_size": len(settled),
                            "population_win_rate": baseline_rate,
                            "comparison_win_rate": comparison_rate,
                            "wins": sum(1 for row in members if str(row.get("outcome") or "").upper() == "WIN"),
                            "losses": sum(1 for row in members if str(row.get("outcome") or "").upper() == "LOSS"),
                            "breakeven": sum(1 for row in members if str(row.get("outcome") or "").upper() == "BREAKEVEN"),
                            "engine_version": self.version,
                            "research_only": True,
                        },
                        warnings=tuple(warnings),
                    )
                )

        return tuple(sorted(candidates, key=lambda item: (-item.confidence_score, -abs(item.uplift or 0.0), item.title)))

    @staticmethod
    def _win_rate(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        wins = sum(1 for row in rows if str(row.get("outcome") or "").upper() == "WIN")
        return round(wins / len(rows) * 100.0, 8)

    @staticmethod
    def _feature_value(row: Mapping[str, Any], key: str) -> Any:
        if key.startswith("feature_vector."):
            return (row.get("feature_vector") or {}).get(key.split(".", 1)[1])
        return row.get(key)

    @staticmethod
    def _discoverable_keys(rows: list[dict[str, Any]]) -> tuple[str, ...]:
        keys = {
            "instrument",
            "planning_horizon",
            "scenario",
            "selected_plan",
            "regime",
            "direction",
            "exit_reason",
        }
        feature_keys: set[str] = set()
        for row in rows:
            for key, value in (row.get("feature_vector") or {}).items():
                if isinstance(value, (str, bool, int)):
                    feature_keys.add(f"feature_vector.{key}")
        return tuple(sorted(keys | feature_keys))

    @staticmethod
    def _confidence_score(*, sample_size: int, population_size: int, uplift: float, r_values: list[float]) -> float:
        sample_component = min(40.0, sqrt(sample_size) / max(1.0, sqrt(population_size)) * 40.0)
        uplift_component = min(40.0, uplift / 25.0 * 40.0)
        consistency_component = 10.0
        if len(r_values) >= 2:
            deviation = pstdev(r_values)
            consistency_component = max(0.0, 20.0 - min(20.0, deviation * 8.0))
        return round(min(100.0, sample_component + uplift_component + consistency_component), 8)

    @staticmethod
    def _stability_score(rows: list[dict[str, Any]]) -> float:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = str(row.get("planning_horizon") or row.get("instrument") or "ALL")
            buckets[key].append(row)
        rates = [PatternDiscoveryEngine._win_rate(items) for items in buckets.values() if items]
        if len(rates) <= 1:
            return 60.0
        dispersion = pstdev(rates)
        return round(max(0.0, min(100.0, 100.0 - dispersion * 2.0)), 8)
