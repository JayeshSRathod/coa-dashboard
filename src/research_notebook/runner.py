"""Deterministic experiment runner for CQRP research evidence.

The runner filters immutable evidence according to a ResearchExperiment,
calculates statistics, evaluates configured thresholds, and produces a completed
ExperimentRun plus a governed ResearchConclusion. It has no broker authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from src.statistics.engine import StatisticsEngine

from .models import ExperimentRun, ResearchConclusion, ResearchExperiment


class ResearchExperimentRunner:
    version = "research-runner-v1"

    def __init__(self, statistics_engine: StatisticsEngine | None = None) -> None:
        self.statistics_engine = statistics_engine or StatisticsEngine()

    def run(
        self,
        experiment: ResearchExperiment,
        evidence_records: Iterable[Mapping[str, Any]],
        *,
        statistics_snapshot_id: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> tuple[ExperimentRun, ResearchConclusion]:
        selected = [dict(row) for row in evidence_records if self._matches(experiment, row)]
        report = self.statistics_engine.calculate(selected)
        metrics = report.as_dict()
        supported, rationale = self._evaluate(experiment, metrics)
        completed_at = datetime.now(timezone.utc).isoformat()

        run = ExperimentRun.new(
            experiment_id=experiment.experiment_id,
            status="COMPLETED",
            evidence_ids=tuple(str(row.get("evidence_id")) for row in selected if row.get("evidence_id")),
            statistics_snapshot_id=statistics_snapshot_id,
            evidence_count=len(selected),
            parameters={
                "runner_version": self.version,
                "evidence_query": dict(experiment.evidence_query),
                **dict(parameters or {}),
            },
            metrics=metrics,
            completed_at=completed_at,
        )

        if len(selected) < experiment.minimum_sample_size:
            conclusion_code = "INCONCLUSIVE"
            governance = "COLLECT_MORE_EVIDENCE"
            summary = (
                f"Experiment has {len(selected)} qualifying evidence records; "
                f"minimum required is {experiment.minimum_sample_size}."
            )
        elif supported:
            conclusion_code = "SUPPORTED"
            governance = "ELIGIBLE_FOR_PATTERN_VALIDATION"
            summary = "Configured research thresholds were satisfied."
        else:
            conclusion_code = "NOT_SUPPORTED"
            governance = "RETAIN_IN_RESEARCH"
            summary = "One or more configured research thresholds were not satisfied."

        conclusion = ResearchConclusion.new(
            experiment_id=experiment.experiment_id,
            run_id=run.run_id,
            conclusion=conclusion_code,
            summary=summary,
            rationale=tuple(rationale),
            statistics_snapshot_id=statistics_snapshot_id,
            evidence_ids=run.evidence_ids,
            governance_recommendation=governance,
        )
        return run, conclusion

    @staticmethod
    def _matches(experiment: ResearchExperiment, record: Mapping[str, Any]) -> bool:
        if experiment.planning_horizons and str(record.get("planning_horizon") or "").upper() not in experiment.planning_horizons:
            return False
        if experiment.instruments and str(record.get("instrument") or "") not in experiment.instruments:
            return False
        if experiment.scenarios and str(record.get("scenario") or "") not in experiment.scenarios:
            return False

        for key, expected in experiment.inclusion_criteria.items():
            actual = record.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        for key, rejected in experiment.exclusion_criteria.items():
            actual = record.get(key)
            if isinstance(rejected, (list, tuple, set)):
                if actual in rejected:
                    return False
            elif actual == rejected:
                return False
        return True

    @staticmethod
    def _evaluate(experiment: ResearchExperiment, metrics: Mapping[str, Any]) -> tuple[bool, list[str]]:
        if not experiment.success_thresholds:
            return False, ["No success thresholds configured."]
        supported = True
        rationale: list[str] = []
        for metric, rule in experiment.success_thresholds.items():
            actual = metrics.get(metric)
            if actual is None:
                supported = False
                rationale.append(f"Metric {metric} is unavailable.")
                continue
            if isinstance(rule, Mapping):
                minimum = rule.get("min")
                maximum = rule.get("max")
            else:
                minimum = rule
                maximum = None
            passed = True
            if minimum is not None and float(actual) < float(minimum):
                passed = False
            if maximum is not None and float(actual) > float(maximum):
                passed = False
            supported = supported and passed
            rationale.append(
                f"{metric}={actual}; threshold={dict(rule) if isinstance(rule, Mapping) else {'min': rule}}; "
                f"result={'PASS' if passed else 'FAIL'}."
            )
        return supported, rationale
