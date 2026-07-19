import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.persistence import initialize_research_database


class ResearchDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(tempfile.mkdtemp()) / "research.db"
        self.repository = initialize_research_database(str(self.db_path))

    def tearDown(self):
        self.repository.connection.close()

    def test_records_traceable_research_events(self):
        profile_id = self.repository.register_strategy_profile(
            name="COA Core v1.0",
            coa_engine_version="1.0.0-baseline",
            validation_engine_version="0.0.0",
            configuration={"eos_method": "average_atm_premium"},
        )
        snapshot_id = self.repository.append_snapshot(
            {
                "instrument": "NIFTY",
                "spot": 25000.0,
                "market_source": "simulated",
                "strategy_profile_id": profile_id,
                "scenario_number": 1,
                "scenario": "Strong range consolidation",
                "risk_mode": "NORMAL_LOTS",
                "support": 24950.0,
                "resistance": 25050.0,
                "eos": 24910.0,
                "eor": 25090.0,
                "coa_payload": {"support_bias": "STABLE"},
                "option_chain": [{"Strike": 25000, "Call_OI": 100}],
                "data_quality_status": "VALID",
            }
        )
        signal_id = self.repository.record_signal(
            {
                "snapshot_id": snapshot_id,
                "instrument": "NIFTY",
                "direction": "CALL",
                "action": "WATCH",
                "trade_allowed": False,
                "rationale": {"reason": "research capture"},
            }
        )
        self.repository.record_validation(
            {
                "signal_id": signal_id,
                "category": "structure",
                "passed": True,
                "score": 0.9,
                "reasons": ["stable range"],
            }
        )
        self.repository.record_system_event(
            "snapshot_captured", "INFO", {"snapshot_id": snapshot_id}, "NIFTY"
        )

        snapshots = self.repository.list_snapshots("NIFTY")
        self.assertEqual(snapshots[0]["snapshot_id"], snapshot_id)
        self.assertEqual(
            self.repository.connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0], 1
        )
        self.assertEqual(
            self.repository.connection.execute("SELECT COUNT(*) FROM signal_validations").fetchone()[0],
            1,
        )

    def test_research_records_are_append_only(self):
        snapshot_id = self.repository.append_snapshot(
            {
                "instrument": "NIFTY",
                "spot": 25000.0,
                "market_source": "simulated",
                "coa_payload": {},
            }
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.connection.execute(
                "UPDATE market_snapshots SET spot = ? WHERE snapshot_id = ?",
                (1.0, snapshot_id),
            )


if __name__ == "__main__":
    unittest.main()
