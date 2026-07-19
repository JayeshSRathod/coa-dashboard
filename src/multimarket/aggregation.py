"""Pure cross-broker position aggregation."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def aggregate_positions(position_sets: Iterable[tuple[str, str, Iterable[dict]]]) -> list[dict]:
    totals = defaultdict(lambda: {"quantity": 0.0, "net_value": 0.0, "accounts": []})
    for broker_name, account_id, positions in position_sets:
        for position in positions:
            instrument_id = position["instrument_id"]
            totals[instrument_id]["quantity"] += float(position.get("quantity", 0))
            totals[instrument_id]["net_value"] += float(position.get("net_value", 0))
            totals[instrument_id]["accounts"].append({"broker": broker_name, "account_id": account_id})
    return [{"instrument_id": key, **value} for key, value in sorted(totals.items())]
