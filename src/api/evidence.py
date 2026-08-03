"""Read-only API facade for immutable CQRP evidence records."""

from __future__ import annotations

from src.persistence.evidence_repository import EvidenceRepository


class EvidenceApiV1:
    prefix = "/api/v1/evidence"

    def __init__(self, repository: EvidenceRepository) -> None:
        self.repository = repository

    def get(self, evidence_id: str) -> dict:
        record = self.repository.get(evidence_id)
        return {
            "status": 200 if record else 404,
            "data": record,
            "mode": "SHADOW_PAPER_ONLY",
        }

    def for_trade(self, trade_id: str) -> dict:
        record = self.repository.get_for_trade(trade_id)
        return {
            "status": 200 if record else 404,
            "data": record,
            "mode": "SHADOW_PAPER_ONLY",
        }

    def history(
        self,
        *,
        instrument: str | None = None,
        outcome: str | None = None,
        scenario_number: int | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> dict:
        rows = self.repository.list(
            instrument=instrument,
            outcome=outcome,
            scenario_number=scenario_number,
            experiment_id=experiment_id,
            limit=limit,
        )
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "SHADOW_PAPER_ONLY",
        }
