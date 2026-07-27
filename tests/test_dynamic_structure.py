import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.persistence import apply_migrations, connect
from src.persistence.schema import RESEARCH_MIGRATIONS
from src.persistence.snapshot_repository import SnapshotRepository
from src.persistence.structure_event_repository import StructureEventRepository
from src.research.dynamic_structure import DynamicStructureEngine
from src.research.models import CapturedSnapshot
from src.research.validation import SnapshotValidationResult


class DynamicStructureTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "research.db"
        self.connection = connect(self.path)
        apply_migrations(self.connection, RESEARCH_MIGRATIONS)
        self.snapshots = SnapshotRepository(self.connection)
        self.events = StructureEventRepository(self.connection)
        self.engine = DynamicStructureEngine(self.events)
        self.coa = SimpleNamespace(coa_result_id=None, scenario_number=7, support=95.0,
                                   resistance=100.0, eos=94.0, eor=104.0, raw_output={})

    def tearDown(self):
        self.connection.close()

    def _snapshot(self, snapshot_id, timestamp, spot, call_volume, call_oi, put_wall=95.0):
        chain = [
            {"Strike": 90.0, "Call_Vol": 20.0, "Call_OI": 20.0, "Call_LTP": 12.0,
             "Put_Vol": 80.0 if put_wall == 90.0 else 30.0, "Put_OI": 60.0, "Put_LTP": 10.0},
            {"Strike": 95.0, "Call_Vol": 50.0, "Call_OI": 50.0, "Call_LTP": 8.0,
             "Put_Vol": 100.0 if put_wall == 95.0 else 20.0, "Put_OI": 100.0, "Put_LTP": 14.0},
            {"Strike": 100.0, "Call_Vol": call_volume, "Call_OI": call_oi, "Call_LTP": 5.0,
             "Put_Vol": 40.0, "Put_OI": 40.0, "Put_LTP": 20.0},
        ]
        record = CapturedSnapshot.new(
            snapshot_id=snapshot_id, session_id="NIFTY:2026-07-27", instrument="NIFTY",
            spot=spot, source="TEST", market_captured_at=timestamp, ingested_at=timestamp,
            option_chain=chain,
        )
        self.snapshots.append(record, SnapshotValidationResult(True, True, 1.0))
        return self.snapshots.get(snapshot_id)

    def test_records_walls_volume_then_oi_confirmation_levels_and_data_gap(self):
        first = self._snapshot("S1", "2026-07-27T09:00:00+05:30", 99.0, 100.0, 100.0)
        self.engine.process(first, coa_result=self.coa)
        second = self._snapshot("S2", "2026-07-27T09:01:00+05:30", 102.0, 130.0, 100.0, put_wall=90.0)
        self.engine.process(second, coa_result=self.coa)
        third = self._snapshot("S3", "2026-07-27T09:06:10+05:30", 103.0, 130.0, 140.0, put_wall=90.0)
        self.engine.process(third, coa_result=self.coa)
        fourth = self._snapshot("S4", "2026-07-27T09:07:00+05:30", 103.2, 130.0, 140.0, put_wall=90.0)
        self.engine.process(fourth, coa_result=self.coa)

        events = self.events.list_events("NIFTY", session_id="NIFTY:2026-07-27")
        types = {item["event_type"] for item in events}
        self.assertIn("WALL_MIGRATED", types)
        self.assertIn("VOLUME_BURST", types)
        self.assertIn("OI_CONFIRMATION", types)
        self.assertIn("RESISTANCE_BREAK", types)
        self.assertIn("FIVE_MINUTE_CONFIRMATION", types)
        self.assertIn("DATA_GAP", types)
        self.assertIn("MOMENTUM_STALL", types)
        self.assertEqual(len(self.events.latest_walls("NIFTY", "NIFTY:2026-07-27")), 12)
        self.assertTrue(all(item["scenario_track"] == "COA1_PLUS_COA2" for item in events))
        self.assertTrue(all(10 <= item["coa2_scenario_number"] <= 18 for item in events))
        self.assertEqual(self.events.list_sessions("NIFTY"), ["NIFTY:2026-07-27"])
        bursts = self.events.list_events(
            "NIFTY", session_id="NIFTY:2026-07-27", event_types=("VOLUME_BURST",)
        )
        self.assertTrue(bursts)
        self.assertTrue(all(item["event_type"] == "VOLUME_BURST" for item in bursts))
        walls = self.events.list_walls("NIFTY", session_id="NIFTY:2026-07-27")
        self.assertTrue(walls)
        self.assertTrue(all(item["strike"] is not None for item in walls))

    def test_structure_records_are_append_only(self):
        snapshot = self._snapshot("S1", "2026-07-27T09:00:00+05:30", 99.0, 100.0, 100.0)
        self.engine.process(snapshot, coa_result=self.coa)
        event = self.events.list_events("NIFTY")[0]
        with self.assertRaises(Exception):
            self.connection.execute(
                "UPDATE dynamic_structure_events SET event_type='CHANGED' WHERE event_id=?",
                (event["event_id"],),
            )


if __name__ == "__main__":
    unittest.main()
