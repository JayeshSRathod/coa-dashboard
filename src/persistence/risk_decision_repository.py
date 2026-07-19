"""Append-only persistence boundary for deterministic portfolio risk decisions."""

from __future__ import annotations

import json
import sqlite3

from src.risk.models import RiskDecision

from .repository import SQLiteRepository


def _decode(row: sqlite3.Row) -> RiskDecision:
    return RiskDecision.new(
        decision_id=row["decision_id"], signal_id=row["signal_id"], portfolio_id=row["portfolio_id"],
        experiment_id=row["experiment_id"], risk_version=row["risk_version"], decision=row["decision"],
        requested_quantity=int(row["requested_quantity"]), approved_quantity=int(row["approved_quantity"]),
        capital_required=float(row["capital_required"]), capital_available=float(row["capital_available"]),
        rejection_reason=row["rejection_reason"], risk_metrics=json.loads(row["risk_metrics_json"]),
        created_at=row["created_at"], created_by=row["created_by"],
    )


class RiskDecisionRepository(SQLiteRepository):
    """Repository for immutable pre-execution risk decisions."""

    def append(self, decision: RiskDecision) -> RiskDecision:
        existing = self.get_for_signal(
            decision.signal_id, decision.portfolio_id, decision.risk_version, decision.experiment_id
        )
        if existing is not None:
            return existing
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO risk_decisions (
                        decision_id, signal_id, portfolio_id, experiment_id, experiment_key, risk_version,
                        decision, requested_quantity, approved_quantity, capital_required, capital_available,
                        rejection_reason, risk_metrics_json, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (decision.decision_id, decision.signal_id, decision.portfolio_id, decision.experiment_id,
                     decision.experiment_id or "", decision.risk_version, decision.decision,
                     decision.requested_quantity, decision.approved_quantity, decision.capital_required,
                     decision.capital_available, decision.rejection_reason,
                     json.dumps(dict(decision.risk_metrics), sort_keys=True, separators=(",", ":"), default=str),
                     decision.created_at, decision.created_by),
                )
        except sqlite3.IntegrityError:
            existing = self.get_for_signal(
                decision.signal_id, decision.portfolio_id, decision.risk_version, decision.experiment_id
            )
            if existing is not None:
                return existing
            raise
        return decision

    def get(self, decision_id: str) -> RiskDecision | None:
        row = self.connection.execute(
            "SELECT * FROM risk_decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        return _decode(row) if row else None

    def get_for_signal(
        self, signal_id: str, portfolio_id: str, risk_version: str, experiment_id: str | None
    ) -> RiskDecision | None:
        row = self.connection.execute(
            "SELECT * FROM risk_decisions WHERE signal_id = ? AND portfolio_id = ? "
            "AND risk_version = ? AND experiment_key = ?",
            (signal_id, portfolio_id, risk_version, experiment_id or ""),
        ).fetchone()
        return _decode(row) if row else None

    def list_for_portfolio(self, portfolio_id: str) -> list[RiskDecision]:
        rows = self.connection.execute(
            "SELECT * FROM risk_decisions WHERE portfolio_id = ? ORDER BY created_at ASC, decision_id ASC",
            (portfolio_id,),
        ).fetchall()
        return [_decode(row) for row in rows]
