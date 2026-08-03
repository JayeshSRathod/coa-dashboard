"""Read-only API facade for CQRP PAPER trade lifecycle projections."""

from __future__ import annotations

from src.execution.lifecycle_service import PaperTradeLifecycleService


class PaperTradeLifecycleApiV1:
    prefix = "/api/v1/paper-trades"

    def __init__(self, service: PaperTradeLifecycleService) -> None:
        self.service = service

    def get_trade(self, trade_id: str) -> dict:
        detail = self.service.detail(trade_id)
        return {
            "status": 200 if detail else 404,
            "data": detail,
            "mode": "PAPER_ONLY",
        }

    def get_summary(self, trade_id: str) -> dict:
        summary = self.service.summary(trade_id)
        return {
            "status": 200 if summary else 404,
            "data": summary.as_dict() if summary else None,
            "mode": "PAPER_ONLY",
        }

    def get_session(self, session_id: str) -> dict:
        rows = self.service.session(session_id)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "PAPER_ONLY",
        }

    def get_experiment(self, experiment_id: str) -> dict:
        rows = self.service.experiment(experiment_id)
        return {
            "status": 200,
            "data": rows,
            "count": len(rows),
            "mode": "PAPER_ONLY",
        }
