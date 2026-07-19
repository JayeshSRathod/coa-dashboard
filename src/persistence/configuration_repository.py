"""Append-only immutable experiment configuration repository."""

from __future__ import annotations

import json
from src.strategy_lab.models import Configuration
from .repository import SQLiteRepository


def _decode(row):
    return Configuration.new(configuration_id=row["configuration_id"], strategy_id=row["strategy_id"],
        values=json.loads(row["configuration_json"]), checksum=row["checksum"], created_at=row["created_at"],
        created_by=row["created_by"])


class ConfigurationRepository(SQLiteRepository):
    def insert(self, configuration: Configuration) -> Configuration:
        row = self.connection.execute("SELECT * FROM strategy_configurations WHERE strategy_id=? AND checksum=?",
                                      (configuration.strategy_id, configuration.checksum)).fetchone()
        if row:
            return _decode(row)
        with self.connection:
            self.connection.execute("INSERT INTO strategy_configurations VALUES (?, ?, ?, ?, ?, ?)",
                (configuration.configuration_id, configuration.strategy_id,
                 json.dumps(dict(configuration.values), sort_keys=True, separators=(",", ":")),
                 configuration.checksum, configuration.created_at, configuration.created_by))
        return configuration

    def get(self, configuration_id):
        row = self.connection.execute("SELECT * FROM strategy_configurations WHERE configuration_id=?",
                                      (configuration_id,)).fetchone()
        return _decode(row) if row else None


    def list_for_strategy(self, strategy_id):
        rows = self.connection.execute(
            "SELECT * FROM strategy_configurations WHERE strategy_id=? ORDER BY created_at, configuration_id",
            (strategy_id,)
        ).fetchall()
        return [_decode(row) for row in rows]
