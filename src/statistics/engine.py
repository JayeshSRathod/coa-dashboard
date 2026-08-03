"""Deterministic portfolio and research statistics from immutable evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev
from types import MappingProxyType
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class StatisticsReport:
    sample_size: int
    wins: int
    losses: int
    breakeven: int
    cancelled: int
    expired: int
    win_rate: float
    loss_rate: float
    total_realized_pnl: float
    average_realized_pnl: float
    average_r_multiple: float | None
    expectancy_r: float | None
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    max_drawdown: float
    recovery_factor: float | None
    average_mfe: float
    average_mae: float
    average_holding_seconds: float | None
    payoff_ratio: float | None
    sqn: float | None
    outcome_counts: Mapping[str, int]
    by_instrument: Mapping[str, Mapping[str, Any]]
    by_scenario: Mapping[str, Mapping[str, Any]]
    by_horizon: Mapping[str, Mapping[str, Any]]
    by_selected_plan: Mapping[str, Mapping[str, Any]]
    engine_version: str = "statistics-v1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "wins": self.wins,
            "losses": self.losses,
            "breakeven": self.breakeven,
            "cancelled": self.cancelled,
            "expired": self.expired,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "total_realized_pnl": self.total_realized_pnl,
            "average_realized_pnl": self.average_realized_pnl,
            "average_r_multiple": self.average_r_multiple,
            "expectancy_r": self.expectancy_r,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "recovery_factor": self.recovery_factor,
            "average_mfe": self.average_mfe,
            "average_mae": self.average_mae,
            "average_holding_seconds": self.average_holding_seconds,
            "payoff_ratio": self.payoff_ratio,
            "sqn": self.sqn,
            "outcome_counts": dict(self.outcome_counts),
            "by_instrument": {key: dict(value) for key, value in self.by_instrument.items()},
            "by_scenario": {key: dict(value) for key, value in self.by_scenario.items()},
            "by_horizon": {key: dict(value) for key, value in self.by_horizon.items()},
            "by_selected_plan": {key: dict(value) for key, value in self.by_selected_plan.items()},
            "engine_version": self.engine_version,
        }


class StatisticsEngine:
    version = "statistics-v1"

    def calculate(self, evidence_records: Iterable[Mapping[str, Any]]) -> StatisticsReport:
        rows = [dict(record) for record in evidence_records]
        outcomes = Counter(str(row.get("outcome") or "UNKNOWN").upper() for row in rows)
        trade_rows = [row for row in rows if str(row.get("outcome") or "").upper() in {"WIN", "LOSS", "BREAKEVEN"}]
        pnl = [float(row.get("realized_pnl") or 0.0) for row in trade_rows]
        r_values = [float(row["realized_r_multiple"]) for row in trade_rows if row.get("realized_r_multiple") is not None]
        wins_pnl = [value for value in pnl if value > 0]
        losses_pnl = [value for value in pnl if value < 0]
        gross_profit = sum(wins_pnl)
        gross_loss_abs = abs(sum(losses_pnl))
        wins = outcomes.get("WIN", 0)
        losses = outcomes.get("LOSS", 0)
        settled = wins + losses + outcomes.get("BREAKEVEN", 0)
        win_rate = (wins / settled * 100.0) if settled else 0.0
        loss_rate = (losses / settled * 100.0) if settled else 0.0
        average_win = mean(wins_pnl) if wins_pnl else None
        average_loss_abs = abs(mean(losses_pnl)) if losses_pnl else None
        payoff = (average_win / average_loss_abs) if average_win is not None and average_loss_abs else None
        expectancy_r = mean(r_values) if r_values else None
        sqn = None
        if len(r_values) >= 2:
            deviation = pstdev(r_values)
            if deviation > 0:
                sqn = sqrt(len(r_values)) * mean(r_values) / deviation
        max_drawdown = self._max_drawdown(pnl)
        total_pnl = sum(pnl)
        recovery = (total_pnl / max_drawdown) if max_drawdown > 0 else None

        return StatisticsReport(
            sample_size=len(rows),
            wins=wins,
            losses=losses,
            breakeven=outcomes.get("BREAKEVEN", 0),
            cancelled=outcomes.get("CANCELLED", 0),
            expired=outcomes.get("EXPIRED", 0),
            win_rate=round(win_rate, 6),
            loss_rate=round(loss_rate, 6),
            total_realized_pnl=round(total_pnl, 8),
            average_realized_pnl=round(mean(pnl), 8) if pnl else 0.0,
            average_r_multiple=round(mean(r_values), 8) if r_values else None,
            expectancy_r=round(expectancy_r, 8) if expectancy_r is not None else None,
            gross_profit=round(gross_profit, 8),
            gross_loss=round(gross_loss_abs, 8),
            profit_factor=round(gross_profit / gross_loss_abs, 8) if gross_loss_abs > 0 else None,
            max_drawdown=round(max_drawdown, 8),
            recovery_factor=round(recovery, 8) if recovery is not None else None,
            average_mfe=round(mean(float(row.get("mfe") or 0.0) for row in trade_rows), 8) if trade_rows else 0.0,
            average_mae=round(mean(float(row.get("mae") or 0.0) for row in trade_rows), 8) if trade_rows else 0.0,
            average_holding_seconds=self._average_optional(trade_rows, "holding_seconds"),
            payoff_ratio=round(payoff, 8) if payoff is not None else None,
            sqn=round(sqn, 8) if sqn is not None else None,
            outcome_counts=MappingProxyType(dict(sorted(outcomes.items()))),
            by_instrument=self._group(rows, "instrument"),
            by_scenario=self._group(rows, "scenario"),
            by_horizon=self._group(rows, "planning_horizon"),
            by_selected_plan=self._group(rows, "selected_plan"),
        )

    @staticmethod
    def _max_drawdown(pnl_values: list[float]) -> float:
        equity = peak = max_drawdown = 0.0
        for value in pnl_values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    @staticmethod
    def _average_optional(rows: list[dict[str, Any]], key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return round(mean(values), 8) if values else None

    @staticmethod
    def _group(rows: list[dict[str, Any]], key: str) -> Mapping[str, Mapping[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            value = row.get(key)
            buckets[str(value if value not in {None, ""} else "UNKNOWN")].append(row)
        result: dict[str, Mapping[str, Any]] = {}
        for bucket, items in buckets.items():
            settled = [item for item in items if str(item.get("outcome") or "").upper() in {"WIN", "LOSS", "BREAKEVEN"}]
            wins = sum(1 for item in settled if str(item.get("outcome") or "").upper() == "WIN")
            pnl = sum(float(item.get("realized_pnl") or 0.0) for item in settled)
            r_values = [float(item["realized_r_multiple"]) for item in settled if item.get("realized_r_multiple") is not None]
            result[bucket] = MappingProxyType({
                "sample_size": len(items),
                "settled_trades": len(settled),
                "wins": wins,
                "win_rate": round((wins / len(settled) * 100.0), 6) if settled else 0.0,
                "total_realized_pnl": round(pnl, 8),
                "average_r_multiple": round(mean(r_values), 8) if r_values else None,
            })
        return MappingProxyType(dict(sorted(result.items())))
