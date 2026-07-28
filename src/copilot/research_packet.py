"""Read-only conversion of CQRP structure evidence into bounded Copilot evidence."""

from __future__ import annotations

from collections import Counter
from typing import Any, Protocol

from .models import EvidenceReference


class ResearchEvidenceSource(Protocol):
    def dynamic_events(self, instrument_id: str, *, session_id: str | None = None,
                       event_types: tuple[str, ...] = (), limit: int = 10_000) -> list[dict[str, object]]: ...
    def dynamic_walls(self, instrument_id: str, *, session_id: str | None = None,
                      limit: int = 25_000) -> list[dict[str, object]]: ...


class ResearchPacketBuilder:
    """Builds a small, cited packet; it never writes, executes, or tunes CQRP."""

    def build(self, source: ResearchEvidenceSource, *, instrument: str,
              session_id: str | None = None, expiry: str | None = None,
              limit: int = 250) -> tuple[EvidenceReference, ...]:
        events = source.dynamic_events(instrument, session_id=session_id, limit=max(1, limit))
        walls = source.dynamic_walls(instrument, session_id=session_id, limit=max(1, limit * 12))
        if expiry:
            events = [item for item in events if item.get("expiry") == expiry]
            walls = [item for item in walls if item.get("expiry") == expiry]
        if not events and not walls:
            return ()
        session_key = session_id or "ALL_SESSIONS"
        expiry_key = expiry or "ALL_EXPIRIES"
        counts = Counter(str(item.get("event_type")) for item in events)
        summary = EvidenceReference.new(
            source="dynamic_structure", entity_type="research_session",
            entity_id=f"{instrument}:{session_key}:{expiry_key}",
            summary=f"{instrument} {session_key} {expiry_key}: {len(events)} structure events and {len(walls)} CE/PE wall records. Event counts: {dict(sorted(counts.items()))}.",
            payload={"instrument": instrument, "session_id": session_id, "expiry": expiry,
                     "event_counts": dict(sorted(counts.items())), "event_count": len(events), "wall_count": len(walls)},
        )
        selected: list[EvidenceReference] = [summary]
        priority = {"FIVE_MINUTE_OUTCOME", "OI_CONFIRMATION", "VOLUME_BURST", "WALL_MIGRATED",
                    "RESISTANCE_BREAK", "FALSE_BREAKOUT", "EOS_REJECTION", "PULLBACK_RETEST",
                    "CONTINUATION_REENTRY", "MOMENTUM_STALL"}
        notable = [item for item in events if str(item.get("event_type")) in priority]
        for event in notable[:2]:
            payload = dict(event.get("payload") or {})
            selected.append(EvidenceReference.new(
                source="dynamic_structure", entity_type="structure_event", entity_id=str(event.get("event_id")),
                summary=self._event_summary(event, payload),
                payload={"event_type": event.get("event_type"), "occurred_at": event.get("occurred_at"),
                         "instrument": event.get("instrument"), "expiry": event.get("expiry"),
                         "scenario_track": event.get("scenario_track"), "strike": payload.get("strike") or payload.get("to_strike"),
                         "spot": payload.get("spot") or payload.get("after_spot"),
                         "level": payload.get("level") or payload.get("resistance") or payload.get("eos"),
                         "five_minute_result": payload.get("result"),
                         "volume_trigger_strike": payload.get("volume_trigger_strike"),
                         "source_event_id": payload.get("source_event_id")},
            ))
        for wall in walls[-1:]:
            payload = dict(wall.get("payload") or {})
            selected.append(EvidenceReference.new(
                source="dynamic_structure", entity_type="option_wall", entity_id=str(wall.get("wall_id")),
                summary=(f"{wall.get('captured_at')}: {wall.get('instrument')} {wall.get('strike')} {wall.get('side')} "
                         f"{wall.get('metric')} rank {wall.get('rank')} = {wall.get('metric_value')}; "
                         f"expiry {wall.get('expiry')}; contract {payload.get('contract')}"),
                payload={"instrument": wall.get("instrument"), "expiry": wall.get("expiry"), "strike": wall.get("strike"),
                         "side": wall.get("side"), "metric": wall.get("metric"), "rank": wall.get("rank"),
                         "metric_value": wall.get("metric_value"), "snapshot_id": wall.get("snapshot_id")},
            ))
        return tuple(selected)

    @staticmethod
    def _event_summary(event: dict[str, Any], payload: dict[str, Any]) -> str:
        return (f"{event.get('occurred_at')}: {event.get('event_type')} for {event.get('instrument')} "
                f"expiry {event.get('expiry')}; strike {payload.get('strike') or payload.get('to_strike')}; "
                f"spot {payload.get('spot') or payload.get('after_spot')}; "
                f"level {payload.get('level') or payload.get('resistance') or payload.get('eos')}; "
                f"five-minute result {payload.get('result')}; volume trigger {payload.get('volume_trigger_strike')}.")
