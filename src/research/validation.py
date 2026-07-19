"""Validation rules applied before a market snapshot reaches persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import CapturedSnapshot


CALL_LTP_KEYS = ("Call_LTP", "CE_LTP", "call_ltp")
PUT_LTP_KEYS = ("Put_LTP", "PE_LTP", "put_ltp")


@dataclass(frozen=True)
class SnapshotValidationResult:
    is_valid: bool
    is_complete: bool
    data_completeness: float
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    missing_strikes: tuple[float, ...] = ()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def _is_positive(value: float | None) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


class SnapshotValidator:
    """Performs deterministic structural, temporal, and metadata validation."""

    def validate(
        self,
        snapshot: CapturedSnapshot,
        previous_market_captured_at: str | None = None,
        previous_session_id: str | None = None,
        previous_expiry: str | None = None,
        previous_expiry_type: str | None = None,
        expected_instrument: str | None = None,
    ) -> SnapshotValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        missing_strikes: list[float] = []

        if not snapshot.instrument.strip():
            errors.append("instrument is required")
        if expected_instrument and snapshot.instrument != expected_instrument:
            errors.append("provider instrument does not match requested instrument")
        if not snapshot.source.strip():
            errors.append("market source is required")
        if not snapshot.session_id.strip():
            errors.append("session_id is required")
        if not _is_positive(snapshot.spot):
            errors.append("spot must be positive")
        if snapshot.futures_price is not None and not _is_positive(snapshot.futures_price):
            errors.append("futures_price must be positive when supplied")
        if snapshot.atm_strike is not None and not _is_positive(snapshot.atm_strike):
            errors.append("atm_strike must be positive when supplied")

        try:
            market_time = _parse_timestamp(snapshot.market_captured_at)
            ingest_time = _parse_timestamp(snapshot.ingested_at)
            if market_time > ingest_time:
                errors.append("market capture time cannot be after ingestion time")
            if previous_market_captured_at and market_time <= _parse_timestamp(previous_market_captured_at):
                errors.append("market capture timestamp is not monotonic")
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid timestamp: {exc}")

        if previous_session_id == snapshot.session_id:
            if previous_expiry and snapshot.expiry and previous_expiry != snapshot.expiry:
                errors.append("expiry changed within the same market session")
            if previous_expiry_type and snapshot.expiry_type and previous_expiry_type != snapshot.expiry_type:
                errors.append("expiry_type changed within the same market session")

        if not isinstance(snapshot.option_chain, list) or not snapshot.option_chain:
            errors.append("option_chain must contain at least one strike")
            return SnapshotValidationResult(False, False, 0.0, tuple(errors))

        valid_rows = 0
        for index, row in enumerate(snapshot.option_chain):
            if not isinstance(row, dict):
                warnings.append(f"option_chain row {index} is not an object")
                continue
            try:
                strike = float(row["Strike"])
                if strike <= 0:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                warnings.append(f"option_chain row {index} has an invalid Strike")
                continue

            valid_rows += 1
            has_call = any(row.get(key) is not None for key in CALL_LTP_KEYS)
            has_put = any(row.get(key) is not None for key in PUT_LTP_KEYS)
            if not (has_call and has_put):
                missing_strikes.append(strike)
                warnings.append(f"strike {strike:g} is missing a call or put quote")

        completeness = valid_rows / len(snapshot.option_chain)
        if valid_rows == 0:
            errors.append("option_chain contains no valid strikes")
        is_complete = not warnings and completeness == 1.0
        return SnapshotValidationResult(
            is_valid=not errors,
            is_complete=is_complete,
            data_completeness=completeness,
            errors=tuple(errors),
            warnings=tuple(warnings),
            missing_strikes=tuple(missing_strikes),
        )
