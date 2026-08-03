"""Immutable domain models for the CQRP Research Notebook backend.

The notebook governs hypotheses, evidence selection, statistical linkage,
experiment runs, observations, and conclusions. It has no broker authority and
operates only on persisted shadow-research artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ALLOWED_STATUS = {"DRAFT", "RUNNING", "COMPLETED", "REJECTED", "PROMOTED", "ARCHIVED"}
_ALLOWED_RUN_STATUS = {"QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"}
_ALLOWED_CONCLUSION = {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "REJECTED", "PROMOTED"}


@dataclass(frozen=True)
class ResearchExperiment:
    experiment_id: str
    title: str
    hypothesis: str
    objective: str
    status: str
    planning_horizons: tuple[str, ...]
    instruments: tuple[str, ...]
    scenarios: tuple[str, ...]
    inclusion_criteria: Mapping[str, Any]
    exclusion_criteria: Mapping[str, Any]
    minimum_sample_size: int
    primary_metric: str
    success_thresholds: Mapping[str, Any]
    evidence_query: Mapping[str, Any]
    tags: tuple[str, ...]
    owner: str
    experiment_version: str
    created_at: str
    created_by: str = "ResearchNotebookService"

    @classmethod
    def new(cls, **values: Any) -> "ResearchExperiment":
        values.setdefault("experiment_id", str(uuid4()))
        values.setdefault("status", "DRAFT")
        values.setdefault("planning_horizons", ())
        values.setdefault("instruments", ())
        values.setdefault("scenarios", ())
        values.setdefault("inclusion_criteria", {})
        values.setdefault("exclusion_criteria", {})
        values.setdefault("minimum_sample_size", 30)
        values.setdefault("primary_metric", "expectancy_r")
        values.setdefault("success_thresholds", {})
        values.setdefault("evidence_query", {})
        values.setdefault("tags", ())
        values.setdefault("owner", "CQRP_RESEARCH")
        values.setdefault("experiment_version", "research-experiment-v1")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "ResearchNotebookService")

        values["status"] = str(values["status"]).upper()
        values["planning_horizons"] = tuple(str(item).upper() for item in values["planning_horizons"])
        values["instruments"] = tuple(str(item) for item in values["instruments"])
        values["scenarios"] = tuple(str(item) for item in values["scenarios"])
        values["tags"] = tuple(str(item) for item in values["tags"])
        values["inclusion_criteria"] = MappingProxyType(dict(values["inclusion_criteria"]))
        values["exclusion_criteria"] = MappingProxyType(dict(values["exclusion_criteria"]))
        values["success_thresholds"] = MappingProxyType(dict(values["success_thresholds"]))
        values["evidence_query"] = MappingProxyType(dict(values["evidence_query"]))

        if not str(values.get("title") or "").strip():
            raise ValueError("title is required")
        if not str(values.get("hypothesis") or "").strip():
            raise ValueError("hypothesis is required")
        if values["status"] not in _ALLOWED_STATUS:
            raise ValueError("unsupported experiment status")
        invalid_horizons = set(values["planning_horizons"]) - {"NEXT_SESSION", "INTRADAY"}
        if invalid_horizons:
            raise ValueError(f"unsupported planning horizons: {sorted(invalid_horizons)}")
        if int(values["minimum_sample_size"]) < 1:
            raise ValueError("minimum_sample_size must be positive")
        values["minimum_sample_size"] = int(values["minimum_sample_size"])
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "hypothesis": self.hypothesis,
            "objective": self.objective,
            "status": self.status,
            "planning_horizons": list(self.planning_horizons),
            "instruments": list(self.instruments),
            "scenarios": list(self.scenarios),
            "inclusion_criteria": dict(self.inclusion_criteria),
            "exclusion_criteria": dict(self.exclusion_criteria),
            "minimum_sample_size": self.minimum_sample_size,
            "primary_metric": self.primary_metric,
            "success_thresholds": dict(self.success_thresholds),
            "evidence_query": dict(self.evidence_query),
            "tags": list(self.tags),
            "owner": self.owner,
            "experiment_version": self.experiment_version,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


@dataclass(frozen=True)
class ExperimentRun:
    run_id: str
    experiment_id: str
    status: str
    evidence_ids: tuple[str, ...]
    statistics_snapshot_id: str | None
    evidence_count: int
    parameters: Mapping[str, Any]
    metrics: Mapping[str, Any]
    started_at: str
    completed_at: str | None
    run_version: str
    created_by: str = "ResearchNotebookService"

    @classmethod
    def new(cls, **values: Any) -> "ExperimentRun":
        values.setdefault("run_id", str(uuid4()))
        values.setdefault("status", "QUEUED")
        values.setdefault("evidence_ids", ())
        values.setdefault("statistics_snapshot_id", None)
        values.setdefault("parameters", {})
        values.setdefault("metrics", {})
        values.setdefault("started_at", _now())
        values.setdefault("completed_at", None)
        values.setdefault("run_version", "research-run-v1")
        values.setdefault("created_by", "ResearchNotebookService")

        values["status"] = str(values["status"]).upper()
        values["evidence_ids"] = tuple(str(item) for item in values["evidence_ids"])
        values["evidence_count"] = int(values.get("evidence_count", len(values["evidence_ids"])))
        values["parameters"] = MappingProxyType(dict(values["parameters"]))
        values["metrics"] = MappingProxyType(dict(values["metrics"]))
        if values["status"] not in _ALLOWED_RUN_STATUS:
            raise ValueError("unsupported run status")
        if values["evidence_count"] < 0:
            raise ValueError("evidence_count cannot be negative")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "statistics_snapshot_id": self.statistics_snapshot_id,
            "evidence_count": self.evidence_count,
            "parameters": dict(self.parameters),
            "metrics": dict(self.metrics),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "run_version": self.run_version,
            "created_by": self.created_by,
        }


@dataclass(frozen=True)
class ResearchObservation:
    observation_id: str
    experiment_id: str
    run_id: str | None
    observation_type: str
    title: str
    body: str
    evidence_ids: tuple[str, ...]
    metrics: Mapping[str, Any]
    author: str
    created_at: str

    @classmethod
    def new(cls, **values: Any) -> "ResearchObservation":
        values.setdefault("observation_id", str(uuid4()))
        values.setdefault("run_id", None)
        values.setdefault("observation_type", "NOTE")
        values.setdefault("evidence_ids", ())
        values.setdefault("metrics", {})
        values.setdefault("author", "CQRP_RESEARCH")
        values.setdefault("created_at", _now())
        values["observation_type"] = str(values["observation_type"]).upper()
        values["evidence_ids"] = tuple(str(item) for item in values["evidence_ids"])
        values["metrics"] = MappingProxyType(dict(values["metrics"]))
        if not str(values.get("body") or "").strip():
            raise ValueError("observation body is required")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "observation_type": self.observation_type,
            "title": self.title,
            "body": self.body,
            "evidence_ids": list(self.evidence_ids),
            "metrics": dict(self.metrics),
            "author": self.author,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ResearchConclusion:
    conclusion_id: str
    experiment_id: str
    run_id: str | None
    conclusion: str
    summary: str
    rationale: tuple[str, ...]
    statistics_snapshot_id: str | None
    evidence_ids: tuple[str, ...]
    governance_recommendation: str
    created_at: str
    created_by: str = "ResearchNotebookService"

    @classmethod
    def new(cls, **values: Any) -> "ResearchConclusion":
        values.setdefault("conclusion_id", str(uuid4()))
        values.setdefault("run_id", None)
        values.setdefault("statistics_snapshot_id", None)
        values.setdefault("evidence_ids", ())
        values.setdefault("rationale", ())
        values.setdefault("governance_recommendation", "RETAIN_IN_RESEARCH")
        values.setdefault("created_at", _now())
        values.setdefault("created_by", "ResearchNotebookService")
        values["conclusion"] = str(values["conclusion"]).upper()
        values["rationale"] = tuple(str(item) for item in values["rationale"])
        values["evidence_ids"] = tuple(str(item) for item in values["evidence_ids"])
        if values["conclusion"] not in _ALLOWED_CONCLUSION:
            raise ValueError("unsupported research conclusion")
        if not str(values.get("summary") or "").strip():
            raise ValueError("conclusion summary is required")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {
            "conclusion_id": self.conclusion_id,
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "conclusion": self.conclusion,
            "summary": self.summary,
            "rationale": list(self.rationale),
            "statistics_snapshot_id": self.statistics_snapshot_id,
            "evidence_ids": list(self.evidence_ids),
            "governance_recommendation": self.governance_recommendation,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
