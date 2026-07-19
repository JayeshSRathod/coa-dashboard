"""Append-only dataset registry for reproducible historical experiments."""

from __future__ import annotations

import json
from src.strategy_lab.models import Dataset
from .repository import SQLiteRepository


def _decode(row):
    return Dataset.new(dataset_id=row["dataset_id"], market=row["market"], source=row["source"],
        symbols=json.loads(row["symbols_json"]), from_date=row["from_date"], to_date=row["to_date"],
        snapshot_count=int(row["snapshot_count"]), checksum=row["checksum"], created_at=row["created_at"],
        created_by=row["created_by"])


class DatasetRepository(SQLiteRepository):
    def insert(self, dataset: Dataset) -> Dataset:
        row = self.connection.execute("SELECT * FROM datasets WHERE checksum=?", (dataset.checksum,)).fetchone()
        if row:
            return _decode(row)
        with self.connection:
            self.connection.execute("INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (dataset.dataset_id, dataset.market, dataset.source, json.dumps(dataset.symbols),
                 dataset.from_date, dataset.to_date, dataset.snapshot_count, dataset.checksum,
                 dataset.created_at, dataset.created_by))
        return dataset

    def get(self, dataset_id):
        row = self.connection.execute("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        return _decode(row) if row else None
