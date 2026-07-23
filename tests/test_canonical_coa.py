from __future__ import annotations
import unittest
import os
import tempfile
from src.coa.canonical import CanonicalCOAEngine
from src.coa.canonical.replay import COAReplayValidator
from src.coa.canonical.versions import RULE_REGISTRY
from src.persistence import initialize_canonical_coa_repository

SNAPSHOT = {
    "snapshot_id": "canonical-snapshot", "session_id": "canonical-session", "market_captured_at": "2026-07-23T10:00:00+05:30", "instrument": "NIFTY", "spot": 25020.0,
    "metadata": {"step_size": 50, "call_oi_change_history": [0.0], "put_oi_change_history": [0.0]},
    "option_chain": [
        {"Strike": 24950, "Call_Vol": 100, "Put_Vol": 300, "Call_LTP": 90, "Put_LTP": 25, "Call_OI": 1000, "Put_OI": 1300},
        {"Strike": 25000, "Call_Vol": 500, "Put_Vol": 100, "Call_LTP": 55, "Put_LTP": 45, "Call_OI": 2000, "Put_OI": 1000},
        {"Strike": 25050, "Call_Vol": 300, "Put_Vol": 500, "Call_LTP": 30, "Put_LTP": 80, "Call_OI": 1600, "Put_OI": 2100},
        {"Strike": 25100, "Call_Vol": 120, "Put_Vol": 80, "Call_LTP": 15, "Put_LTP": 120, "Call_OI": 900, "Put_OI": 800},
    ],
}

class CanonicalCOATests(unittest.TestCase):
    def test_state_is_immutable_explainable_and_deterministic(self):
        engine = CanonicalCOAEngine(); first, second = engine.analyze(SNAPSHOT), engine.analyze(SNAPSHOT)
        self.assertEqual(first, second); self.assertEqual(first.engine_version, "COA-Canonical-1.0.0"); self.assertEqual(len(first.evidence), 4)
        with self.assertRaises(TypeError): first.structural.dominance["support"] = "X"
    def test_canonical_structure_matches_frozen_baseline(self):
        comparison = COAReplayValidator().compare(SNAPSHOT)
        self.assertTrue(comparison.matches_legacy); self.assertEqual(comparison.differences, {})
    def test_rules_evidence_and_replay_are_append_only_records(self):
        handle, path = tempfile.mkstemp(suffix=".sqlite"); os.close(handle)
        try:
            repository = initialize_canonical_coa_repository(path); engine = CanonicalCOAEngine(); state = engine.analyze(SNAPSHOT)
            repository.register_rules(RULE_REGISTRY); repository.append_state(state); repository.append_replay(COAReplayValidator(engine).compare(SNAPSHOT), engine.engine_version)
            self.assertEqual(repository.connection.execute("SELECT COUNT(*) FROM coa_rule_registry").fetchone()[0], 4)
            self.assertEqual(repository.connection.execute("SELECT COUNT(*) FROM coa_evidence").fetchone()[0], 4)
            self.assertEqual(repository.connection.execute("SELECT matches_legacy FROM coa_replay").fetchone()[0], 1)
            repository.connection.close()
        finally: os.unlink(path)
