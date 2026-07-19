"""Append-only experiment definitions and deterministic execution results."""

from __future__ import annotations

import json
from src.strategy_lab.models import Experiment, ExperimentRun
from .repository import SQLiteRepository


def _experiment(row):
    return Experiment.new(experiment_id=row["experiment_id"], strategy_id=row["strategy_id"],
        experiment_name=row["experiment_name"], objective=row["objective"], hypothesis=row["hypothesis"],
        dataset_id=row["dataset_id"], configuration_id=row["configuration_id"], market=row["market"],
        symbols=json.loads(row["symbols_json"]), from_date=row["from_date"], to_date=row["to_date"],
        execution_mode=row["execution_mode"], status=row["status"], notes=row["notes"],
        created_at=row["created_at"], created_by=row["created_by"])


def _run(row):
    return ExperimentRun.new(run_id=row["run_id"], experiment_id=row["experiment_id"],
        input_fingerprint=row["input_fingerprint"], status=row["status"],
        execution_time_ms=float(row["execution_time_ms"]), results=json.loads(row["results_json"]),
        occurred_at=row["occurred_at"], created_at=row["created_at"])


class ExperimentRepository(SQLiteRepository):
    def insert(self, experiment: Experiment) -> Experiment:
        row = self.connection.execute("SELECT * FROM experiments WHERE strategy_id=? AND experiment_name=?",
                                      (experiment.strategy_id, experiment.experiment_name)).fetchone()
        if row:
            return _experiment(row)
        with self.connection:
            self.connection.execute("INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (experiment.experiment_id, experiment.strategy_id, experiment.experiment_name,
                 experiment.objective, experiment.hypothesis, experiment.dataset_id,
                 experiment.configuration_id, experiment.market, json.dumps(experiment.symbols),
                 experiment.from_date, experiment.to_date, experiment.execution_mode, experiment.status,
                 experiment.notes, experiment.created_at, experiment.created_by))
        return experiment

    def get(self, experiment_id):
        row = self.connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        return _experiment(row) if row else None

    def append_run(self, run: ExperimentRun) -> ExperimentRun:
        row = self.connection.execute("SELECT * FROM experiment_runs WHERE experiment_id=? AND input_fingerprint=?",
                                      (run.experiment_id, run.input_fingerprint)).fetchone()
        if row:
            return _run(row)
        with self.connection:
            self.connection.execute("INSERT INTO experiment_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run.run_id, run.experiment_id, run.input_fingerprint, run.status, run.execution_time_ms,
                 json.dumps(dict(run.results), sort_keys=True, separators=(",", ":")),
                 run.occurred_at, run.created_at))
        return run

    def list_runs(self, experiment_ids):
        ids = tuple(experiment_ids)
        if not ids:
            return []
        rows = self.connection.execute(
            f"SELECT * FROM experiment_runs WHERE experiment_id IN ({','.join('?' * len(ids))}) "
            "ORDER BY experiment_id, occurred_at", ids).fetchall()
        return [_run(row) for row in rows]
