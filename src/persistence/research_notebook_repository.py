"""Append-only persistence for CQRP Research Notebook artifacts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.research_notebook.models import (
    ExperimentRun,
    ResearchConclusion,
    ResearchExperiment,
    ResearchObservation,
)

from .repository import SQLiteRepository


def install_research_notebook_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS research_experiments (
            experiment_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            objective TEXT NOT NULL,
            status TEXT NOT NULL,
            planning_horizons_json TEXT NOT NULL,
            instruments_json TEXT NOT NULL,
            scenarios_json TEXT NOT NULL,
            inclusion_criteria_json TEXT NOT NULL,
            exclusion_criteria_json TEXT NOT NULL,
            minimum_sample_size INTEGER NOT NULL,
            primary_metric TEXT NOT NULL,
            success_thresholds_json TEXT NOT NULL,
            evidence_query_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            owner TEXT NOT NULL,
            experiment_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS research_experiment_runs (
            run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_ids_json TEXT NOT NULL,
            statistics_snapshot_id TEXT,
            evidence_count INTEGER NOT NULL,
            parameters_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            run_version TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(experiment_id) REFERENCES research_experiments(experiment_id)
        );

        CREATE TABLE IF NOT EXISTS research_observations (
            observation_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            run_id TEXT,
            observation_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            evidence_ids_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(experiment_id) REFERENCES research_experiments(experiment_id),
            FOREIGN KEY(run_id) REFERENCES research_experiment_runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS research_conclusions (
            conclusion_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            run_id TEXT,
            conclusion TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale_json TEXT NOT NULL,
            statistics_snapshot_id TEXT,
            evidence_ids_json TEXT NOT NULL,
            governance_recommendation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY(experiment_id) REFERENCES research_experiments(experiment_id),
            FOREIGN KEY(run_id) REFERENCES research_experiment_runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS research_notebook_entries (
            entry_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_research_experiments_status_time
            ON research_experiments(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_research_runs_experiment_time
            ON research_experiment_runs(experiment_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_research_observations_experiment_time
            ON research_observations(experiment_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_research_conclusions_experiment_time
            ON research_conclusions(experiment_id, created_at);

        CREATE TRIGGER IF NOT EXISTS research_experiments_no_update
            BEFORE UPDATE ON research_experiments BEGIN
            SELECT RAISE(ABORT, 'research_experiments is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_experiments_no_delete
            BEFORE DELETE ON research_experiments BEGIN
            SELECT RAISE(ABORT, 'research_experiments is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_runs_no_update
            BEFORE UPDATE ON research_experiment_runs BEGIN
            SELECT RAISE(ABORT, 'research_experiment_runs is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_runs_no_delete
            BEFORE DELETE ON research_experiment_runs BEGIN
            SELECT RAISE(ABORT, 'research_experiment_runs is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_observations_no_update
            BEFORE UPDATE ON research_observations BEGIN
            SELECT RAISE(ABORT, 'research_observations is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_observations_no_delete
            BEFORE DELETE ON research_observations BEGIN
            SELECT RAISE(ABORT, 'research_observations is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_conclusions_no_update
            BEFORE UPDATE ON research_conclusions BEGIN
            SELECT RAISE(ABORT, 'research_conclusions is append-only');
            END;
        CREATE TRIGGER IF NOT EXISTS research_conclusions_no_delete
            BEFORE DELETE ON research_conclusions BEGIN
            SELECT RAISE(ABORT, 'research_conclusions is append-only');
            END;
        """
    )


class ResearchNotebookRepository(SQLiteRepository):
    """Persistence boundary for immutable notebook artifacts."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        install_research_notebook_schema(connection)

    def append_experiment(self, experiment: ResearchExperiment) -> str:
        values = experiment.as_dict()
        with self.connection:
            self.connection.execute(
                "INSERT INTO research_experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    values["experiment_id"], values["title"], values["hypothesis"], values["objective"], values["status"],
                    self._json(values["planning_horizons"]), self._json(values["instruments"]), self._json(values["scenarios"]),
                    self._json(values["inclusion_criteria"]), self._json(values["exclusion_criteria"]), values["minimum_sample_size"],
                    values["primary_metric"], self._json(values["success_thresholds"]), self._json(values["evidence_query"]),
                    self._json(values["tags"]), values["owner"], values["experiment_version"], values["created_at"], values["created_by"],
                ),
            )
        return experiment.experiment_id

    def append_run(self, run: ExperimentRun) -> str:
        values = run.as_dict()
        with self.connection:
            self.connection.execute(
                "INSERT INTO research_experiment_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    values["run_id"], values["experiment_id"], values["status"], self._json(values["evidence_ids"]),
                    values["statistics_snapshot_id"], values["evidence_count"], self._json(values["parameters"]),
                    self._json(values["metrics"]), values["started_at"], values["completed_at"], values["run_version"], values["created_by"],
                ),
            )
        return run.run_id

    def append_observation(self, observation: ResearchObservation) -> str:
        values = observation.as_dict()
        with self.connection:
            self.connection.execute(
                "INSERT INTO research_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    values["observation_id"], values["experiment_id"], values["run_id"], values["observation_type"],
                    values["title"], values["body"], self._json(values["evidence_ids"]), self._json(values["metrics"]),
                    values["author"], values["created_at"],
                ),
            )
        return observation.observation_id

    def append_conclusion(self, conclusion: ResearchConclusion) -> str:
        values = conclusion.as_dict()
        with self.connection:
            self.connection.execute(
                "INSERT INTO research_conclusions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    values["conclusion_id"], values["experiment_id"], values["run_id"], values["conclusion"], values["summary"],
                    self._json(values["rationale"]), values["statistics_snapshot_id"], self._json(values["evidence_ids"]),
                    values["governance_recommendation"], values["created_at"], values["created_by"],
                ),
            )
        return conclusion.conclusion_id

    def append(self, *, experiment_id: str, entry_type: str, content: Any, entry_id: str | None = None) -> str:
        """Backward-compatible generic notebook entry append."""
        entry_id = entry_id or str(uuid4())
        with self.connection:
            self.connection.execute(
                "INSERT INTO research_notebook_entries VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry_id, experiment_id, entry_type,
                    self._json(content), datetime.now(timezone.utc).isoformat(), "StrategyLab",
                ),
            )
        return entry_id

    def list_for_experiment(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM research_notebook_entries WHERE experiment_id=? ORDER BY created_at, entry_id",
            (experiment_id,),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["content"] = json.loads(item.pop("content_json"))
            items.append(item)
        return items

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM research_experiments WHERE experiment_id=?", (experiment_id,)
        ).fetchone()
        return self._decode_experiment(row) if row else None

    def list_experiments(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM research_experiments WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status=?"
            params.append(status.upper())
        query += " ORDER BY created_at DESC, experiment_id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return [self._decode_experiment(row) for row in self.connection.execute(query, params).fetchall()]

    def list_runs(self, experiment_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM research_experiment_runs WHERE experiment_id=? ORDER BY started_at DESC, run_id DESC LIMIT ?",
            (experiment_id, max(1, min(int(limit), 1000))),
        ).fetchall()
        return [self._decode_run(row) for row in rows]

    def list_observations(self, experiment_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM research_observations WHERE experiment_id=? ORDER BY created_at DESC, observation_id DESC LIMIT ?",
            (experiment_id, max(1, min(int(limit), 2000))),
        ).fetchall()
        return [self._decode_observation(row) for row in rows]

    def list_conclusions(self, experiment_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM research_conclusions WHERE experiment_id=? ORDER BY created_at DESC, conclusion_id DESC LIMIT ?",
            (experiment_id, max(1, min(int(limit), 1000))),
        ).fetchall()
        return [self._decode_conclusion(row) for row in rows]

    def experiment_detail(self, experiment_id: str) -> dict[str, Any] | None:
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            return None
        return {
            "experiment": experiment,
            "runs": self.list_runs(experiment_id),
            "observations": self.list_observations(experiment_id),
            "conclusions": self.list_conclusions(experiment_id),
            "entries": self.list_for_experiment(experiment_id),
        }

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, default=str)

    @staticmethod
    def _load(item: dict[str, Any], *fields: str) -> dict[str, Any]:
        for field in fields:
            item[field.removesuffix("_json")] = json.loads(item.pop(field))
        return item

    @classmethod
    def _decode_experiment(cls, row: sqlite3.Row) -> dict[str, Any]:
        return cls._load(dict(row), "planning_horizons_json", "instruments_json", "scenarios_json", "inclusion_criteria_json", "exclusion_criteria_json", "success_thresholds_json", "evidence_query_json", "tags_json")

    @classmethod
    def _decode_run(cls, row: sqlite3.Row) -> dict[str, Any]:
        return cls._load(dict(row), "evidence_ids_json", "parameters_json", "metrics_json")

    @classmethod
    def _decode_observation(cls, row: sqlite3.Row) -> dict[str, Any]:
        return cls._load(dict(row), "evidence_ids_json", "metrics_json")

    @classmethod
    def _decode_conclusion(cls, row: sqlite3.Row) -> dict[str, Any]:
        return cls._load(dict(row), "rationale_json", "evidence_ids_json")
