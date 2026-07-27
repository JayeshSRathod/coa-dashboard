"""Deterministic dynamic CE/PE wall and COA-level event recorder.

This module observes persisted research data. It has no authority to create
signals, change frozen COA mathematics, approve risk, or submit orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from engine.coa2_momentum import (
    classify_line_state, classify_tactical_scenario, compute_side_oi_change_pct,
)
from src.common.version import DYNAMIC_STRUCTURE_VERSION
from src.persistence.structure_event_repository import StructureEventRepository


@dataclass(frozen=True)
class DynamicStructureConfig:
    top_walls: int = 3
    volume_burst_minimum: float = 1.0
    oi_confirmation_minimum: float = 1.0
    level_tolerance_ratio: float = 0.10
    minimum_level_tolerance: float = 1.0
    data_gap_seconds: float = 90.0
    five_minute_seconds: float = 300.0


@dataclass(frozen=True)
class StructureProcessingOutcome:
    snapshot_id: str
    wall_count: int
    event_ids: tuple[str, ...]


class DynamicStructureEngine:
    """Derives replayable market-structure evidence from chronological snapshots."""

    version = DYNAMIC_STRUCTURE_VERSION

    def __init__(self, repository: StructureEventRepository,
                 config: DynamicStructureConfig | None = None) -> None:
        self.repository = repository
        self.config = config or DynamicStructureConfig()

    def process(self, snapshot: dict[str, Any], *, coa_result: Any | None = None,
                validation_result: Any | None = None, signal: Any | None = None,
                risk_decision: Any | None = None, paper_trade_id: str | None = None) -> StructureProcessingOutcome:
        previous_walls = self.repository.latest_walls(snapshot["instrument"], snapshot["session_id"])
        history = list(reversed(self.repository.list_events(
            snapshot["instrument"], session_id=snapshot["session_id"], limit=500
        )))
        walls = self._walls(snapshot)
        for wall in walls:
            self.repository.append_wall(wall)
        context = self._context(snapshot, history, coa_result, validation_result, signal, risk_decision, paper_trade_id)
        events = self._events(snapshot, walls, previous_walls, history, context)
        event_ids = tuple(self.repository.append_event(event) for event in events)
        return StructureProcessingOutcome(snapshot["snapshot_id"], len(walls), event_ids)

    def _walls(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        rows = snapshot.get("option_chain") or []
        output: list[dict[str, Any]] = []
        mappings = (("CE", "VOLUME", "Call_Vol"), ("CE", "OI", "Call_OI"),
                    ("PE", "VOLUME", "Put_Vol"), ("PE", "OI", "Put_OI"))
        for side, metric, key in mappings:
            ranked = sorted(
                (row for row in rows if self._number(row.get("Strike")) is not None),
                key=lambda row: (self._number(row.get(key)) or 0.0, self._number(row.get("Strike")) or 0.0),
                reverse=True,
            )[:self.config.top_walls]
            for rank, row in enumerate(ranked, start=1):
                output.append({
                    "snapshot_id": snapshot["snapshot_id"], "session_id": snapshot["session_id"],
                    "instrument": snapshot["instrument"], "captured_at": snapshot["market_captured_at"],
                    "side": side, "metric": metric, "rank": rank,
                    "strike": self._number(row.get("Strike")),
                    "metric_value": self._number(row.get(key)) or 0.0,
                    "payload": {"engine_version": self.version, "option_chain_row": dict(row)},
                })
        return output

    def _events(self, snapshot: dict[str, Any], walls: list[dict[str, Any]],
                previous_walls: list[dict[str, Any]], history: list[dict[str, Any]],
                context: dict[str, Any]) -> list[dict[str, Any]]:
        # This lightweight event is the replay anchor for spot/level crossing
        # logic. It is evidence, not a trade event.
        events: list[dict[str, Any]] = [self._event(snapshot, context, "STRUCTURE_SNAPSHOT", "snapshot", {
            "spot": float(snapshot["spot"]), "data_quality_status": snapshot.get("data_quality_status"),
            "call_oi_total": self._total_oi(snapshot, "Call_OI"),
            "put_oi_total": self._total_oi(snapshot, "Put_OI"),
            "levels": {name: getattr(context.get("coa_result"), name.lower(), None)
                       for name in ("SUPPORT", "RESISTANCE", "EOS", "EOR")},
        })]
        now = self._time(snapshot["market_captured_at"])
        previous_by_key = {(row["side"], row["metric"], row["rank"]): row for row in previous_walls}
        current_by_key = {(row["side"], row["metric"], row["rank"]): row for row in walls}
        previous_time = self._time(previous_walls[0]["captured_at"]) if previous_walls else None
        if previous_time and (now - previous_time).total_seconds() > self.config.data_gap_seconds:
            events.append(self._event(snapshot, context, "DATA_GAP", "session", {
                "gap_seconds": round((now - previous_time).total_seconds(), 3),
                "threshold_seconds": self.config.data_gap_seconds,
            }))
        if snapshot.get("data_quality_status") != "VALID" or not bool(snapshot.get("is_complete", True)):
            events.append(self._event(snapshot, context, "FEED_QUALITY_DEGRADED", "quality", {
                "data_quality_status": snapshot.get("data_quality_status"),
                "is_complete": snapshot.get("is_complete"),
                "missing_strikes": snapshot.get("missing_strikes", []),
            }))
        for key, current in current_by_key.items():
            previous = previous_by_key.get(key)
            if previous and current["strike"] != previous["strike"]:
                events.append(self._event(snapshot, context, "WALL_MIGRATED", ":".join(map(str, key)), {
                    "side": current["side"], "metric": current["metric"], "rank": current["rank"],
                    "from_strike": previous["strike"], "to_strike": current["strike"],
                    "from_value": previous["metric_value"], "to_value": current["metric_value"],
                }))
        for side in ("CE", "PE"):
            current_volume = current_by_key.get((side, "VOLUME", 1))
            previous_volume = previous_by_key.get((side, "VOLUME", 1))
            current_oi = current_by_key.get((side, "OI", 1))
            previous_oi = previous_by_key.get((side, "OI", 1))
            volume_delta = self._same_strike_delta(current_volume, previous_volume)
            oi_delta = self._same_strike_delta(current_oi, previous_oi)
            if volume_delta is not None and volume_delta >= self.config.volume_burst_minimum:
                events.append(self._event(snapshot, context, "VOLUME_BURST", side, {
                    "side": side, "strike": current_volume["strike"], "volume_delta": volume_delta,
                    "current_volume": current_volume["metric_value"],
                }))
            prior_volume_burst = self._last(history, "VOLUME_BURST", side)
            if oi_delta is not None and oi_delta >= self.config.oi_confirmation_minimum:
                event_type = "OI_CONFIRMATION" if prior_volume_burst else "OI_BUILD"
                events.append(self._event(snapshot, context, event_type, side, {
                    "side": side, "strike": current_oi["strike"], "oi_delta": oi_delta,
                    "current_oi": current_oi["metric_value"],
                    "sequence": "VOLUME_FIRST_OI_LATER" if prior_volume_burst else "OI_WITHOUT_RECORDED_VOLUME_BURST",
                }))
        events.extend(self._level_events(snapshot, context, history, previous_walls, walls))
        last_break = self._last(history, "RESISTANCE_BREAK", "RESISTANCE")
        previous_snapshot = self._last_snapshot_payload(history)
        current_signal_events = {event["event_type"] for event in events}
        tolerance = max(self.config.minimum_level_tolerance, self._strike_step(walls) * self.config.level_tolerance_ratio)
        if last_break and previous_snapshot and abs(float(snapshot["spot"]) - float(previous_snapshot.get("spot", snapshot["spot"]))) <= tolerance and not ({"VOLUME_BURST", "OI_CONFIRMATION"} & current_signal_events):
            events.append(self._event(snapshot, context, "MOMENTUM_STALL", "BREAKOUT", {
                "spot": float(snapshot["spot"]), "previous_spot": previous_snapshot.get("spot"),
                "tolerance": tolerance, "paper_exit_candidate": True,
                "automatic_exit": False,
            }))
        return events

    def _level_events(self, snapshot: dict[str, Any], context: dict[str, Any],
                      history: list[dict[str, Any]], previous_walls: list[dict[str, Any]],
                      walls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        coa = context.get("coa_result")
        if coa is None:
            return []
        output: list[dict[str, Any]] = []
        levels = {"SUPPORT": coa.support, "RESISTANCE": coa.resistance, "EOS": coa.eos, "EOR": coa.eor}
        spot = float(snapshot["spot"])
        step = self._strike_step(walls)
        tolerance = max(self.config.minimum_level_tolerance, step * self.config.level_tolerance_ratio)
        prior_snapshot = self._last_snapshot_payload(history)
        prior_spot = prior_snapshot.get("spot") if prior_snapshot else None
        prior_levels = prior_snapshot.get("levels", {}) if prior_snapshot else {}
        for name, level in levels.items():
            if level is None:
                continue
            level = float(level)
            prior_level = prior_levels.get(name)
            if prior_level is not None and float(prior_level) != level:
                output.append(self._event(snapshot, context, "LEVEL_MIGRATED", name, {
                    "level": name, "from_level": float(prior_level), "to_level": level,
                    "spot": spot,
                }))
            distance = spot - level
            if abs(distance) <= tolerance:
                output.append(self._event(snapshot, context, f"{name}_TOUCH", name, {
                    "spot": spot, "level": level, "tolerance": tolerance,
                }))
            if name == "RESISTANCE":
                last_break = self._last(history, "RESISTANCE_BREAK", "RESISTANCE")
                if prior_spot is not None and float(prior_spot) <= level + tolerance and spot > level + tolerance:
                    output.append(self._event(snapshot, context, "RESISTANCE_BREAK", "RESISTANCE", {"spot": spot, "resistance": level}))
                elif last_break and spot > level + tolerance:
                    elapsed = (self._time(snapshot["market_captured_at"]) - self._time(last_break["occurred_at"])).total_seconds()
                    output.append(self._event(snapshot, context,
                        "FIVE_MINUTE_CONFIRMATION" if elapsed >= self.config.five_minute_seconds else "BREAKOUT_SUSTAINED",
                        "RESISTANCE", {"spot": spot, "resistance": level, "elapsed_seconds": elapsed}))
                elif last_break and spot <= level + tolerance:
                    output.append(self._event(snapshot, context, "FALSE_BREAKOUT", "RESISTANCE", {"spot": spot, "resistance": level}))
            if name == "EOS":
                last_touch = self._last(history, "EOS_TOUCH", "EOS")
                if prior_spot is not None and float(prior_spot) <= level + tolerance and spot > level + tolerance:
                    output.append(self._event(snapshot, context, "EOS_REJECTION", "EOS", {"spot": spot, "eos": level}))
                elif prior_spot is not None and float(prior_spot) >= level - tolerance and spot < level - tolerance:
                    output.append(self._event(snapshot, context, "EOS_BREAK", "EOS", {"spot": spot, "eos": level}))
                elif last_touch and spot > level + tolerance:
                    elapsed = (self._time(snapshot["market_captured_at"]) - self._time(last_touch["occurred_at"])).total_seconds()
                    if elapsed >= self.config.five_minute_seconds:
                        output.append(self._event(snapshot, context, "FIVE_MINUTE_CONFIRMATION", "EOS", {"spot": spot, "eos": level, "elapsed_seconds": elapsed}))
        # A retest is a pullback to an already-broken resistance. Continuation is
        # only recorded after that retest, so it is useful for paper-only re-entry analysis.
        resistance = levels["RESISTANCE"]
        if resistance is not None:
            last_break = self._last(history, "RESISTANCE_BREAK", "RESISTANCE")
            last_retest = self._last(history, "PULLBACK_RETEST", "RESISTANCE")
            if last_break and abs(spot - float(resistance)) <= tolerance:
                output.append(self._event(snapshot, context, "PULLBACK_RETEST", "RESISTANCE", {"spot": spot, "resistance": resistance}))
            elif last_retest and spot > float(resistance) + tolerance:
                output.append(self._event(snapshot, context, "CONTINUATION_REENTRY", "RESISTANCE", {"spot": spot, "resistance": resistance}))
        return output

    def _context(self, snapshot: dict[str, Any], history: list[dict[str, Any]],
                 coa_result: Any | None, validation_result: Any | None,
                 signal: Any | None, risk_decision: Any | None, paper_trade_id: str | None) -> dict[str, Any]:
        raw = dict(getattr(coa_result, "raw_output", {}) or {})
        coa1 = getattr(coa_result, "scenario_number", None)
        tactical = self._tactical_state(snapshot, history)
        # Combined scenario IDs are stable for analytics: COA1 is 1–9 and
        # COA2 is 10–18, while the payload retains COA2's native 1–9 ID.
        coa2 = 9 + int(tactical["number"])
        track = "COA1_PLUS_COA2" if coa1 is not None else "COA2_TACTICAL"
        outcome = "NO_PAPER_CANDIDATE"
        if paper_trade_id:
            outcome = "PAPER_CANDIDATE"
        elif signal is not None and signal.signal_type in {"BUY", "SELL"}:
            outcome = "RISK_" + str(getattr(risk_decision, "decision", "PENDING"))
        return {"coa_result": coa_result, "coa_result_id": getattr(coa_result, "coa_result_id", None),
                "validation_id": getattr(validation_result, "validation_id", None), "signal_id": getattr(signal, "signal_id", None),
                "risk_decision_id": getattr(risk_decision, "decision_id", None), "paper_trade_id": paper_trade_id,
                "coa1": coa1, "coa2": coa2, "track": track, "outcome": outcome,
                "tactical": tactical}

    def _event(self, snapshot: dict[str, Any], context: dict[str, Any], event_type: str,
               event_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"snapshot_id": snapshot["snapshot_id"], "session_id": snapshot["session_id"],
                "instrument": snapshot["instrument"], "occurred_at": snapshot["market_captured_at"],
                "event_type": event_type, "event_key": event_key, "scenario_track": context["track"],
                "coa1_scenario_number": context["coa1"], "coa2_scenario_number": context["coa2"],
                "coa_result_id": context["coa_result_id"], "validation_id": context["validation_id"],
                "signal_id": context["signal_id"], "risk_decision_id": context["risk_decision_id"],
                "paper_trade_id": context["paper_trade_id"], "outcome_state": context["outcome"],
                "payload": {"engine_version": self.version, "coa2_tactical": context["tactical"], **payload},
                "created_at": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _tactical_state(self, snapshot: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
        payloads = [event["payload"] for event in history if event["event_type"] == "STRUCTURE_SNAPSHOT"]
        totals = [(float(payload.get("call_oi_total", 0.0)), float(payload.get("put_oi_total", 0.0))) for payload in payloads]
        totals.append((self._total_oi(snapshot, "Call_OI"), self._total_oi(snapshot, "Put_OI")))
        call_history = [compute_side_oi_change_pct(current, previous) for (previous, _), (current, _) in zip(totals, totals[1:])]
        put_history = [compute_side_oi_change_pct(current, previous) for (_, previous), (_, current) in zip(totals, totals[1:])]
        timestamp = self._time(snapshot["market_captured_at"])
        return classify_tactical_scenario(
            classify_line_state(call_history), classify_line_state(put_history), now=timestamp
        )

    def _total_oi(self, snapshot: dict[str, Any], key: str) -> float:
        return round(sum(self._number(row.get(key)) or 0.0 for row in snapshot.get("option_chain") or []), 6)

    @staticmethod
    def _same_strike_delta(current: dict[str, Any] | None, previous: dict[str, Any] | None) -> float | None:
        if not current or not previous or current["strike"] != previous["strike"]:
            return None
        return round(float(current["metric_value"]) - float(previous["metric_value"]), 6)

    @staticmethod
    def _time(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _last(history: Iterable[dict[str, Any]], event_type: str, event_key: str) -> dict[str, Any] | None:
        return next((event for event in reversed(list(history)) if event["event_type"] == event_type and event["event_key"] == event_key), None)

    @staticmethod
    def _last_snapshot_payload(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
        events = list(history)
        snapshot_events = [event for event in events if event["event_type"] == "STRUCTURE_SNAPSHOT"]
        return dict(snapshot_events[-1]["payload"]) if snapshot_events else {}

    @staticmethod
    def _strike_step(walls: list[dict[str, Any]]) -> float:
        strikes = sorted({float(item["strike"]) for item in walls})
        diffs = [right - left for left, right in zip(strikes, strikes[1:]) if right > left]
        return min(diffs) if diffs else 10.0
