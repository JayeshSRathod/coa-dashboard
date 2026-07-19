import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.coa.adapter import FrozenCOAAdapter
from src.coa.models import COAResearchResult
from src.persistence import initialize_coa_result_repository, initialize_snapshot_repository
from src.research.models import CapturedSnapshot
from src.research.coa_pipeline import COAResearchPipeline
from src.research.validation import SnapshotValidationResult


def snapshot_values(snapshot_id: str, captured_at: str, *, valid_chain: bool = True) -> CapturedSnapshot:
    chain = [
        {"Strike": 24900, "Call_Vol": 50, "Put_Vol": 300, "Call_LTP": 140, "Put_LTP": 25},
        {"Strike": 24950, "Call_Vol": 80, "Put_Vol": 500, "Call_LTP": 105, "Put_LTP": 35},
        {"Strike": 25000, "Call_Vol": 120, "Put_Vol": 450, "Call_LTP": 70, "Put_LTP": 55},
        {"Strike": 25050, "Call_Vol": 400, "Put_Vol": 150, "Call_LTP": 42, "Put_LTP": 85},
        {"Strike": 25100, "Call_Vol": 600, "Put_Vol": 90, "Call_LTP": 25, "Put_LTP": 125},
    ]
    if not valid_chain:
        del chain[0]["Put_LTP"]
    return CapturedSnapshot(
        snapshot_id=snapshot_id,
        session_id="NIFTY:2026-07-19",
        instrument="NIFTY",
        spot=25020.0,
        source="test",
        market_captured_at=captured_at,
        ingested_at="2026-07-19T09:16:00+00:00",
        option_chain=chain,
        metadata={"step_size": 50, "strategy_version": "COA Core v1.0"},
    )


class COAResearchTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(tempfile.mkdtemp()) / "research.db"
        self.snapshots = initialize_snapshot_repository(str(self.db_path))
        self.results = initialize_coa_result_repository(str(self.db_path))
        self.adapter = FrozenCOAAdapter()
        self.pipeline = COAResearchPipeline(self.snapshots, self.results, self.adapter)
        self.valid = SnapshotValidationResult(True, True, 1.0)

    def tearDown(self):
        self.snapshots.connection.close()
        self.results.connection.close()

    def _store(self, snapshot):
        self.snapshots.append(snapshot, self.valid)

    def test_adapter_is_deterministic_and_does_not_mutate_snapshot(self):
        snapshot = snapshot_values("snapshot-1", "2026-07-19T09:15:00+00:00")
        record = {
            "snapshot_id": snapshot.snapshot_id, "session_id": snapshot.session_id,
            "instrument": snapshot.instrument, "spot": snapshot.spot,
            "market_captured_at": snapshot.market_captured_at,
            "option_chain": copy.deepcopy(snapshot.option_chain),
            "metadata": copy.deepcopy(snapshot.metadata),
        }
        original = copy.deepcopy(record)
        first = self.adapter.analyze(record)
        second = self.adapter.analyze(record)

        self.assertEqual(first.analytical_values(), second.analytical_values())
        self.assertEqual(record, original)
        self.assertIsNone(first.momentum)
        self.assertIsNone(first.diversion)

    def test_pipeline_persists_and_protects_duplicate_processing(self):
        snapshot = snapshot_values("snapshot-2", "2026-07-19T09:15:00+00:00")
        self._store(snapshot)

        first = self.pipeline.process_snapshot_id(snapshot.snapshot_id, experiment_id="EXP-004")
        second = self.pipeline.process_snapshot_id(snapshot.snapshot_id, experiment_id="EXP-004")

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.result.coa_result_id, second.result.coa_result_id)
        self.assertEqual(len(self.results.list_by_snapshot(snapshot.snapshot_id)), 1)

    def test_session_replay_preserves_snapshot_order_and_result_values(self):
        earlier = snapshot_values("snapshot-3a", "2026-07-19T09:15:00+00:00")
        later = snapshot_values("snapshot-3b", "2026-07-19T09:16:00+00:00")
        self._store(earlier)
        self._store(later)

        outcomes = self.pipeline.process_session(earlier.session_id)

        self.assertEqual([outcome.snapshot_id for outcome in outcomes], [earlier.snapshot_id, later.snapshot_id])
        self.assertTrue(all(outcome.success for outcome in outcomes))
        self.assertEqual(
            outcomes[0].result.analytical_values(),
            self.adapter.analyze(self.snapshots.get(earlier.snapshot_id)).analytical_values(),
        )

    def test_malformed_snapshot_is_recorded_without_stopping_session(self):
        bad = snapshot_values("snapshot-4a", "2026-07-19T09:15:00+00:00", valid_chain=False)
        good = snapshot_values("snapshot-4b", "2026-07-19T09:16:00+00:00")
        self._store(bad)
        self._store(good)

        outcomes = self.pipeline.process_session(good.session_id)

        self.assertFalse(outcomes[0].success)
        self.assertTrue(outcomes[1].success)
        events = self.snapshots.list_events("coa_analysis_failed")
        self.assertEqual(events[0]["payload"]["snapshot_id"], bad.snapshot_id)

    def test_foreign_key_failure_rolls_back_result_insert(self):
        result = COAResearchResult.new(
            snapshot_id="missing-snapshot", session_id="test", experiment_id=None,
            strategy_version="COA Core v1.0", engine_version="1.0.0-baseline",
            scenario_number=None, scenario=None, eos=None, eor=None, support=None,
            resistance=None, momentum=None, diversion=None, trend=None, direction=None,
            risk_mode=None, raw_output={}, processing_time_ms=1.0,
            market_timestamp="2026-07-19T09:15:00+00:00",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.results.append(result)
        count = self.results.connection.execute("SELECT COUNT(*) FROM coa_results").fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
