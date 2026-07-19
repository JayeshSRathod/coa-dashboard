"""Research-only bridge from persisted signals to immutable portfolio risk decisions."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from src.persistence.exposure_repository import ExposureRepository
from src.persistence.portfolio_repository import PortfolioRepository
from src.persistence.risk_decision_repository import RiskDecisionRepository
from src.persistence.signal_repository import SignalRepository
from src.risk.engine import PortfolioRiskEngine
from src.risk.models import RiskDecision

from .observability import emit_snapshot_event


@dataclass(frozen=True)
class RiskProcessingOutcome:
    signal_id: str
    success: bool
    decision: RiskDecision | None = None
    error: str | None = None


class PortfolioRiskPipeline:
    """Evaluate eligible research signals; this class never creates paper trades."""

    def __init__(
        self,
        signal_repository: SignalRepository,
        portfolio_repository: PortfolioRepository,
        risk_decision_repository: RiskDecisionRepository,
        exposure_repository: ExposureRepository,
        risk_engine: PortfolioRiskEngine,
        logger: logging.Logger | None = None,
    ) -> None:
        self.signal_repository = signal_repository
        self.portfolio_repository = portfolio_repository
        self.risk_decision_repository = risk_decision_repository
        self.exposure_repository = exposure_repository
        self.risk_engine = risk_engine
        self.logger = logger or logging.getLogger("cqrp.portfolio_risk")

    def evaluate_signal(
        self, signal_id: str, portfolio_id: str, *, experiment_id: str | None = None
    ) -> RiskProcessingOutcome:
        signal = self.signal_repository.get_signal(signal_id)
        portfolio = self.portfolio_repository.get(portfolio_id)
        if signal is None:
            return RiskProcessingOutcome(signal_id, False, error="signal not found")
        if portfolio is None:
            return RiskProcessingOutcome(signal_id, False, error="portfolio not found")

        existing = self.risk_decision_repository.get_for_signal(
            signal_id, portfolio_id, self.risk_engine.config.risk_version, experiment_id
        )
        if existing is not None:
            return RiskProcessingOutcome(signal_id, True, decision=existing)

        latest = self.exposure_repository.latest(portfolio_id) or {}
        invested = self.exposure_repository.capital_reserved(portfolio_id)
        emit_snapshot_event(
            self.logger, "portfolio_risk_started", signal_id=signal_id, portfolio_id=portfolio_id,
            risk_version=self.risk_engine.config.risk_version,
        )
        try:
            decision = self.risk_engine.evaluate(
                signal, portfolio, invested=invested, total_risk=float(latest.get("total_risk", 0.0)),
                open_positions=int(latest.get("open_positions", 0)),
                daily_pnl=float(latest.get("realized_pnl", 0.0)),
                max_drawdown=float(latest.get("max_drawdown", 0.0)),
                instrument_exposure=float(latest.get("invested_amount", 0.0)),
                experiment_id=experiment_id,
            )
            stored = self.risk_decision_repository.append(decision)
            if stored.decision in {"APPROVED", "REDUCED_SIZE"}:
                self.exposure_repository.append_capital_event(
                    portfolio_id=portfolio_id, decision_id=stored.decision_id,
                    event_type="CAPITAL_RESERVED", amount=stored.capital_required,
                    payload={"signal_id": signal_id, "approved_quantity": stored.approved_quantity},
                )
                self.exposure_repository.append_exposure(
                    portfolio_id=portfolio_id, source_snapshot_id=signal.snapshot_id,
                    instrument=signal.instrument, expiry=signal.expiry, option_type=None,
                    invested_amount=invested + stored.capital_required,
                    total_risk=float(latest.get("total_risk", 0.0))
                    + float(stored.risk_metrics["approved_risk"]),
                    open_positions=int(latest.get("open_positions", 0)) + 1,
                    realized_pnl=float(latest.get("realized_pnl", 0.0)),
                    unrealized_pnl=float(latest.get("unrealized_pnl", 0.0)),
                    total_equity=float(latest.get("total_equity", portfolio.initial_capital)),
                    max_drawdown=float(latest.get("max_drawdown", 0.0)),
                    payload={"decision_id": stored.decision_id, "signal_id": signal_id},
                )
        except Exception as exc:
            emit_snapshot_event(
                self.logger, "portfolio_risk_failed", signal_id=signal_id,
                portfolio_id=portfolio_id, error=str(exc),
            )
            return RiskProcessingOutcome(signal_id, False, error=str(exc))

        emit_snapshot_event(
            self.logger, "portfolio_risk_decided", signal_id=signal_id,
            portfolio_id=portfolio_id, decision_id=stored.decision_id, decision=stored.decision,
            approved_quantity=stored.approved_quantity, capital_required=stored.capital_required,
        )
        return RiskProcessingOutcome(signal_id, True, decision=stored)
