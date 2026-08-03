"""Deterministic availability audit for optional market-data fields.

The audit is deliberately separate from signal, validation and execution code.
It answers whether captured provider fields are sufficiently present to justify
a later shadow study; it does not assign a trading score.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable


_SIDE_FIELDS = {
    "bid": ("Call_Bid", "Put_Bid"),
    "ask": ("Call_Ask", "Put_Ask"),
    "oi_change": ("Call_OI_Change", "Put_OI_Change"),
    "iv": ("Call_IV", "Put_IV"),
    "delta": ("Call_Delta", "Put_Delta"),
    "gamma": ("Call_Gamma", "Put_Gamma"),
    "theta": ("Call_Theta", "Put_Theta"),
    "vega": ("Call_Vega", "Put_Vega"),
}


@dataclass(frozen=True)
class FieldCoverage:
    field: str
    observed_contract_sides: int
    available_contract_sides: int

    @property
    def coverage_percent(self) -> float:
        if not self.observed_contract_sides:
            return 0.0
        return round(100 * self.available_contract_sides / self.observed_contract_sides, 2)

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "coverage_percent": self.coverage_percent}


@dataclass(frozen=True)
class MarketDataAvailabilityReport:
    instrument: str
    expiry: str | None
    snapshot_count: int
    option_row_count: int
    valid_snapshot_count: int
    field_coverage: tuple[FieldCoverage, ...]

    @property
    def provider_fields_ready_for_shadow_study(self) -> bool:
        """Conservative availability gate; not a performance-promotion decision."""
        required = {item.field: item.coverage_percent for item in self.field_coverage}
        return (
            self.snapshot_count > 0
            and self.valid_snapshot_count == self.snapshot_count
            and required.get("bid", 0.0) >= 90.0
            and required.get("ask", 0.0) >= 90.0
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "expiry": self.expiry,
            "snapshot_count": self.snapshot_count,
            "option_row_count": self.option_row_count,
            "valid_snapshot_count": self.valid_snapshot_count,
            "field_coverage": [item.as_dict() for item in self.field_coverage],
            "provider_fields_ready_for_shadow_study": self.provider_fields_ready_for_shadow_study,
        }


class MarketDataAvailabilityAuditor:
    """Calculate presence/quality evidence from immutable stored snapshots."""

    def audit(self, snapshots: Iterable[dict[str, Any]]) -> tuple[MarketDataAvailabilityReport, ...]:
        groups: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
        for snapshot in snapshots:
            groups[(str(snapshot["instrument"]), snapshot.get("expiry"))].append(snapshot)

        reports = [self._report(instrument, expiry, records) for (instrument, expiry), records in groups.items()]
        return tuple(sorted(reports, key=lambda report: (report.instrument, report.expiry or "")))

    def _report(
        self,
        instrument: str,
        expiry: str | None,
        snapshots: list[dict[str, Any]],
    ) -> MarketDataAvailabilityReport:
        observed = {field: 0 for field in _SIDE_FIELDS}
        available = {field: 0 for field in _SIDE_FIELDS}
        option_row_count = 0

        for snapshot in snapshots:
            for row in snapshot.get("option_chain", []) or []:
                option_row_count += 1
                for field, side_columns in _SIDE_FIELDS.items():
                    for column in side_columns:
                        observed[field] += 1
                        value = row.get(column)
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            # Provider data is only "available" when it is usable.  Zero is
                            # valid for an OI change, but not for an executable bid/ask price.
                            if field in {"bid", "ask"} and value <= 0:
                                continue
                            available[field] += 1

        coverage = tuple(
            FieldCoverage(field, observed[field], available[field]) for field in _SIDE_FIELDS
        )
        return MarketDataAvailabilityReport(
            instrument=instrument,
            expiry=expiry,
            snapshot_count=len(snapshots),
            option_row_count=option_row_count,
            valid_snapshot_count=sum(
                1 for snapshot in snapshots if snapshot.get("data_quality_status") == "VALID"
            ),
            field_coverage=coverage,
        )
