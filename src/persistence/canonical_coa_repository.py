"""Append-only audit boundary for the canonical COA domain."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from src.coa.canonical.models import CanonicalCOAState, RuleVersion
from src.coa.canonical.replay import ReplayComparison
from .repository import SQLiteRepository
def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _json(value: object) -> str: return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
class CanonicalCOARepository(SQLiteRepository):
    def register_rules(self, rules: tuple[RuleVersion, ...]) -> None:
        with self.connection:
            for rule in rules: self.connection.execute("INSERT OR IGNORE INTO coa_rule_registry VALUES (?, ?, ?, ?)", (rule.rule_id, rule.version, rule.description, _now()))
    def append_state(self, state: CanonicalCOAState) -> CanonicalCOAState:
        with self.connection:
            for item in state.evidence:
                self.connection.execute("INSERT OR IGNORE INTO coa_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), state.snapshot_id, item.rule_id, item.rule_version, item.result, item.weight, item.comment, item.timestamp, _json({"engine_version": state.engine_version, "recommendation": state.recommendation, "confidence": state.confidence})))
            self.connection.execute("INSERT OR IGNORE INTO coa_versions VALUES (?, ?, ?, ?)", (str(uuid4()), state.engine_version, _json({"engine_version": state.engine_version}), _now()))
        return state
    def append_replay(self, replay: ReplayComparison, canonical_version: str) -> ReplayComparison:
        with self.connection: self.connection.execute("INSERT OR IGNORE INTO coa_replay VALUES (?, ?, ?, ?, ?, ?)", (str(uuid4()), replay.snapshot_id, canonical_version, int(replay.matches_legacy), _json(dict(replay.differences)), _now()))
        return replay
