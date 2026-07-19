"""Configuration-driven conversion of validated research into candidate signals."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter

from src.coa.models import COAResearchResult
from src.validation.models import ValidationResult

from .config import SignalConfig
from .models import ResearchSignal


class SignalEngine:
    """Creates explainable research recommendations, never orders or positions."""

    created_by = "SignalEngine"

    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()

    @property
    def signal_version(self) -> str:
        return self.config.signal_version

    def generate(
        self,
        snapshot: Mapping[str, object],
        coa_result: COAResearchResult,
        validation_result: ValidationResult,
        *,
        experiment_id: str | None = None,
    ) -> ResearchSignal:
        started = perf_counter()
        requested_direction = self.config.direction_for(coa_result.scenario_number)
        reasons = []
        warnings = list(validation_result.warning_reasons)
        failed_checks = []
        if requested_direction is None:
            failed_checks.append("scenario is not enabled by the configured signal rules")
        if not validation_result.is_valid:
            failed_checks.append("validation record is not research-valid")
        if validation_result.overall_score < self.config.minimum_confidence:
            failed_checks.append("confidence is below the configured minimum")
        if validation_result.volume_score < self.config.minimum_volume_score:
            failed_checks.append("volume evidence is below the configured minimum")
        if validation_result.oi_score < self.config.minimum_oi_score:
            failed_checks.append("open-interest evidence is below the configured minimum")
        if validation_result.liquidity_score < self.config.minimum_liquidity_score:
            failed_checks.append("liquidity evidence is below the configured minimum")

        signal_type = requested_direction
        direction = requested_direction
        entry = target_1 = target_2 = None
        if requested_direction is None:
            signal_type = "NO_SIGNAL"
            direction = None
        elif failed_checks:
            signal_type = "WATCHLIST"
        else:
            if requested_direction == "BUY":
                entry, target_2 = coa_result.eos, coa_result.eor
            else:
                entry, target_2 = coa_result.eor, coa_result.eos
            if coa_result.eos is not None and coa_result.eor is not None:
                target_1 = (coa_result.eos + coa_result.eor) / 2
            reasons.append("configured scenario and validation thresholds are satisfied")
        reasons.extend(failed_checks)
        if signal_type == "WATCHLIST":
            reasons.insert(0, "configured scenario is present but validation evidence is incomplete")
        if signal_type == "NO_SIGNAL":
            reasons.insert(0, "no configured directional scenario applies")

        return ResearchSignal.new(
            snapshot_id=coa_result.snapshot_id, coa_result_id=coa_result.coa_result_id,
            validation_id=validation_result.validation_id, session_id=coa_result.session_id,
            experiment_id=experiment_id, strategy_version=coa_result.strategy_version,
            signal_version=self.signal_version, instrument=str(snapshot.get("instrument") or ""),
            expiry=snapshot.get("expiry"), signal_type=signal_type, signal_state="NEW",
            direction=direction, entry_price=entry, stop_loss=None, target_1=target_1,
            target_2=target_2, trailing_reference=None,
            confidence_score=validation_result.overall_score,
            confidence_band=validation_result.confidence_band, scenario=coa_result.scenario,
            eos=coa_result.eos, eor=coa_result.eor, momentum=coa_result.momentum,
            diversion=coa_result.diversion, reasons=reasons, warnings=warnings,
            details={"thresholds": {
                "minimum_confidence": self.config.minimum_confidence,
                "minimum_volume_score": self.config.minimum_volume_score,
                "minimum_oi_score": self.config.minimum_oi_score,
                "minimum_liquidity_score": self.config.minimum_liquidity_score,
            }, "validation_id": validation_result.validation_id,
                "scenario_number": coa_result.scenario_number},
            processing_time_ms=(perf_counter() - started) * 1000,
            created_by=self.created_by,
        )
