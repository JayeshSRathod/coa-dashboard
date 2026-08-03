"""Deterministic validation of CQRP pattern candidates on unseen evidence.

The engine excludes discovery evidence, applies the pattern definition to unseen
settled evidence, measures degradation and stability, and returns a governed
research recommendation. It never promotes an executable trading rule directly.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping

from src.pattern_discovery.models import PatternCandidate

from .models import ValidationMetric, ValidationResult


class ExperimentValidationEngine:
    version = "experiment-validation-v1"

    def __init__(
        self,
        *,
        minimum_validation_sample: int = 20,
        maximum_win_rate_degradation_points: float = 15.0,
        minimum_out_of_sample_win_rate: float = 50.0,
        minimum_validation_score: float = 75.0,
    ) -> None:
        if minimum_validation_sample < 2:
            raise ValueError("minimum_validation_sample must be at least 2")
        self.minimum_validation_sample = int(minimum_validation_sample)
        self.maximum_win_rate_degradation_points = float(maximum_win_rate_degradation_points)
        self.minimum_out_of_sample_win_rate = float(minimum_out_of_sample_win_rate)
        self.minimum_validation_score = float(minimum_validation_score)

    def validate(
        self,
        pattern: PatternCandidate | Mapping[str, Any],
        evidence_records: Iterable[Mapping[str, Any]],
    ) -> ValidationResult:
        candidate = pattern if isinstance(pattern, PatternCandidate) else PatternCandidate.new(**dict(pattern))
        rows = [dict(row) for row in evidence_records]
        settled = [row for row in rows if str(row.get("outcome") or "").upper() in {"WIN", "LOSS", "BREAKEVEN"}]
        discovery_ids = set(candidate.evidence_ids)
        unseen = [row for row in settled if str(row.get("evidence_id") or "") not in discovery_ids]
        matched = [row for row in unseen if self._matches(row, candidate.definition.feature_conditions)]

        warnings: list[str] = []
        if len(matched) < self.minimum_validation_sample:
            warnings.append("Validation sample is below the configured minimum.")

        in_sample_win = float(candidate.support_rate)
        out_sample_win = self._win_rate(matched) if matched else None
        in_sample_expectancy = candidate.expectancy_r
        out_sample_expectancy = self._mean_r(matched)
        degradation = None if out_sample_win is None else round(in_sample_win - out_sample_win, 8)

        stability = self._segment_stability(matched)
        walk_forward = self._walk_forward_score(matched)
        bootstrap = self._bootstrap_proxy(matched)
        monte_carlo = self._sequence_robustness(matched)
        drift = self._drift_score(matched)
        sensitivity = self._sensitivity_score(candidate, unseen)
        sample_score = min(100.0, len(matched) / self.minimum_validation_sample * 100.0)
        oos_score = 0.0 if out_sample_win is None else max(0.0, min(100.0, out_sample_win))

        score = (
            sample_score * 0.25
            + stability * 0.20
            + oos_score * 0.20
            + walk_forward * 0.15
            + monte_carlo * 0.10
            + drift * 0.05
            + sensitivity * 0.05
        )
        score = round(max(0.0, min(100.0, score)), 8)

        passed_oos = (
            out_sample_win is not None
            and out_sample_win >= self.minimum_out_of_sample_win_rate
            and (degradation is None or degradation <= self.maximum_win_rate_degradation_points)
        )
        sufficient_sample = len(matched) >= self.minimum_validation_sample

        if sufficient_sample and passed_oos and score >= self.minimum_validation_score:
            status = "PASSED"
            recommendation = "ELIGIBLE_FOR_RULE_QUALIFICATION"
        elif not sufficient_sample:
            status = "INCONCLUSIVE"
            recommendation = "COLLECT_MORE_EVIDENCE"
        elif score < 50.0 or not passed_oos:
            status = "FAILED"
            recommendation = "REJECT_PATTERN"
        else:
            status = "INCONCLUSIVE"
            recommendation = "RETURN_TO_RESEARCH"

        metrics = (
            ValidationMetric.new(name="validation_sample", value=float(len(matched)), threshold=float(self.minimum_validation_sample), passed=sufficient_sample, weight=25.0),
            ValidationMetric.new(name="out_of_sample_win_rate", value=out_sample_win, threshold=self.minimum_out_of_sample_win_rate, passed=passed_oos if out_sample_win is not None else None, weight=20.0),
            ValidationMetric.new(name="stability_score", value=stability, threshold=60.0, passed=stability >= 60.0, weight=20.0),
            ValidationMetric.new(name="walk_forward_score", value=walk_forward, threshold=55.0, passed=walk_forward >= 55.0, weight=15.0),
            ValidationMetric.new(name="monte_carlo_proxy", value=monte_carlo, threshold=55.0, passed=monte_carlo >= 55.0, weight=10.0),
            ValidationMetric.new(name="drift_score", value=drift, threshold=60.0, passed=drift >= 60.0, weight=5.0),
            ValidationMetric.new(name="sensitivity_score", value=sensitivity, threshold=50.0, passed=sensitivity >= 50.0, weight=5.0),
            ValidationMetric.new(name="bootstrap_score", value=bootstrap, threshold=55.0, passed=bootstrap >= 55.0, weight=0.0),
        )

        return ValidationResult.new(
            pattern_id=candidate.pattern_id,
            experiment_id=candidate.experiment_id,
            status=status,
            recommendation=recommendation,
            validation_score=score,
            discovery_sample_size=candidate.sample_size,
            validation_sample_size=len(matched),
            in_sample_win_rate=in_sample_win,
            out_of_sample_win_rate=out_sample_win,
            in_sample_expectancy_r=in_sample_expectancy,
            out_of_sample_expectancy_r=out_sample_expectancy,
            degradation_percent=degradation,
            stability_score=stability,
            walk_forward_score=walk_forward,
            bootstrap_score=bootstrap,
            monte_carlo_score=monte_carlo,
            drift_score=drift,
            sensitivity_score=sensitivity,
            metrics=metrics,
            evidence_ids=tuple(str(row.get("evidence_id")) for row in matched if row.get("evidence_id")),
            discovery_evidence_ids=tuple(candidate.evidence_ids),
            warnings=tuple(warnings),
            lineage={
                "pattern_version": candidate.pattern_version,
                "discovery_method": candidate.discovery_method,
                "validation_engine_version": self.version,
                "research_only": True,
            },
        )

    @staticmethod
    def _matches(row: Mapping[str, Any], conditions: Mapping[str, Any]) -> bool:
        for key, expected in conditions.items():
            actual = (row.get("feature_vector") or {}).get(key.split(".", 1)[1]) if key.startswith("feature_vector.") else row.get(key)
            if actual != expected:
                return False
        return True

    @staticmethod
    def _win_rate(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        wins = sum(1 for row in rows if str(row.get("outcome") or "").upper() == "WIN")
        return round(wins / len(rows) * 100.0, 8)

    @staticmethod
    def _mean_r(rows: list[dict[str, Any]]) -> float | None:
        values = [float(row["realized_r_multiple"]) for row in rows if row.get("realized_r_multiple") is not None]
        return round(mean(values), 8) if values else None

    @classmethod
    def _segment_stability(cls, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = str(row.get("regime") or row.get("instrument") or row.get("planning_horizon") or "ALL")
            buckets[key].append(row)
        rates = [cls._win_rate(items) for items in buckets.values() if items]
        if len(rates) <= 1:
            return 60.0
        return round(max(0.0, 100.0 - pstdev(rates) * 2.0), 8)

    @classmethod
    def _walk_forward_score(cls, rows: list[dict[str, Any]]) -> float:
        if len(rows) < 4:
            return 0.0
        ordered = sorted(rows, key=lambda row: str(row.get("created_at") or row.get("trade_id") or ""))
        chunk = max(1, len(ordered) // 4)
        rates = [cls._win_rate(ordered[index:index + chunk]) for index in range(0, len(ordered), chunk)]
        positive = sum(1 for rate in rates if rate >= 50.0)
        return round(positive / len(rates) * 100.0, 8)

    @staticmethod
    def _bootstrap_proxy(rows: list[dict[str, Any]]) -> float:
        r_values = [float(row["realized_r_multiple"]) for row in rows if row.get("realized_r_multiple") is not None]
        if len(r_values) < 2:
            return 0.0
        deviation = pstdev(r_values)
        average = mean(r_values)
        return round(max(0.0, min(100.0, 50.0 + average * 20.0 - deviation * 10.0)), 8)

    @staticmethod
    def _sequence_robustness(rows: list[dict[str, Any]]) -> float:
        pnl = [float(row.get("realized_pnl") or 0.0) for row in rows]
        if not pnl:
            return 0.0
        equity = peak = max_drawdown = 0.0
        for value in pnl:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        total = sum(pnl)
        if total <= 0:
            return max(0.0, 40.0 - min(40.0, max_drawdown / max(1.0, abs(total) + 1.0) * 10.0))
        ratio = total / max(1.0, max_drawdown)
        return round(max(0.0, min(100.0, 50.0 + ratio * 10.0)), 8)

    @classmethod
    def _drift_score(cls, rows: list[dict[str, Any]]) -> float:
        if len(rows) < 4:
            return 50.0
        ordered = sorted(rows, key=lambda row: str(row.get("created_at") or row.get("trade_id") or ""))
        midpoint = len(ordered) // 2
        first = cls._win_rate(ordered[:midpoint])
        second = cls._win_rate(ordered[midpoint:])
        return round(max(0.0, 100.0 - abs(first - second) * 2.0), 8)

    @classmethod
    def _sensitivity_score(cls, candidate: PatternCandidate, unseen: list[dict[str, Any]]) -> float:
        conditions = dict(candidate.definition.feature_conditions)
        if len(conditions) != 1:
            return 50.0
        key, expected = next(iter(conditions.items()))
        if not isinstance(expected, (int, float)) or isinstance(expected, bool):
            return 60.0
        neighbours = []
        for delta in (-1, 1):
            condition = {key: expected + delta}
            matched = [row for row in unseen if cls._matches(row, condition)]
            if matched:
                neighbours.append(cls._win_rate(matched))
        if not neighbours:
            return 40.0
        base = candidate.support_rate
        return round(max(0.0, 100.0 - mean(abs(base - value) for value in neighbours) * 2.0), 8)
