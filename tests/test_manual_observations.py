import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.persistence import initialize_manual_observation_repository
from src.research.manual_observations import ManualObservation, ManualObservationService


class ManualObservationTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "research.db"
        self.repository = initialize_manual_observation_repository(str(self.path))
        self.service = ManualObservationService(str(self.path))

    def tearDown(self):
        self.repository.connection.close()
        self.service.close()

    def test_records_and_lists_immutable_manual_evidence(self):
        observation = ManualObservation(
            observed_at=datetime.now(timezone.utc).isoformat(), session_date="2026-07-27",
            instrument="NIFTY", event_type="SUPPORT_RESISTANCE_MIGRATION",
            scenario_number=7, spot=23962.0, support=23950.0, resistance=24000.0,
            narrative="Put-side volume and OI migrated support upward.",
            metadata={"review_window": "five_minutes"},
        )
        observation_id = self.service.record(observation)
        rows = self.repository.list(instrument="NIFTY")
        self.assertEqual(rows[0]["observation_id"], observation_id)
        self.assertEqual(rows[0]["source"], "MANUAL")
        self.assertEqual(rows[0]["metadata"]["review_window"], "five_minutes")
        with self.assertRaises(Exception):
            self.repository.connection.execute(
                "UPDATE manual_observations SET narrative = 'changed' WHERE observation_id = ?",
                (observation_id,),
            )

    def test_rejects_blank_narrative_and_unknown_event(self):
        common = dict(observed_at="2026-07-27T09:00:00+05:30", session_date="2026-07-27", instrument="NIFTY")
        with self.assertRaises(ValueError):
            self.service.record(ManualObservation(**common, event_type="OTHER", narrative=""))
        with self.assertRaises(ValueError):
            self.service.record(ManualObservation(**common, event_type="NOT_A_REAL_EVENT", narrative="note"))
