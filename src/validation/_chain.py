"""Shared, side-effect-free option-chain readers for validation components."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def number(row: Mapping[str, Any], aliases: tuple[str, ...]) -> float | None:
    for name in aliases:
        value = row.get(name)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            return None
    return None


def rows(snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    chain = snapshot.get("option_chain")
    return [row for row in chain if isinstance(row, Mapping)] if isinstance(chain, list) else []


def selected_strike(snapshot: Mapping[str, Any], coa_raw: Mapping[str, Any]) -> float | None:
    metadata = snapshot.get("metadata") or {}
    if isinstance(metadata, Mapping) and metadata.get("selected_strike") is not None:
        try:
            return float(metadata["selected_strike"])
        except (TypeError, ValueError):
            return None
    for key in ("base_strike", "support", "resistance"):
        value = coa_raw.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return snapshot.get("atm_strike")
