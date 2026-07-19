import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.coa.models import COAResearchResult
from src.persistence import (
    initialize_coa_result_repository,
    initialize_snapshot_repository,
    initialize_validation_repository,
)
from src.research.models import CapturedSnapshot
from src.research.validation import SnapshotValidationResult
from src.research.validation_pipeline import ValidationResearchPipeline
from src.validation.config import ValidationConfig
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult
from src.validation.scoring import confidence_band, weighted_score


def make_snapshot(snapshot_id: str, timestamp: str) -> CapturedSnapshot:
    return CapturedSnapshot(
        snapshot_id=snapshot_id,
        session_id="NIFTY:2026-07-19",
        instrument="NIFTY",
        spot=25020.0,
        futures_price=25030.0,
        source="test",
        source_latency_ms=100,
        market_captured_at=timestamp,
        ingested_at="2026-07-19T09:30:00+00:00",
        option_chain=[
            {"Strike": 24950, "Call_Vol": 100, "Put_Vol": 150, "Call_OI": 400,
             "Put_OI": 600, "Call_LTP": 75, "Put_LTP": 35, "Call_Bid": 74, "Call_Ask": 75},
            {"Strike": 25000, "Call_Vol": 200, "Put_Vol": 180, "Call_OI": 800,
             "Put_OI": 750, "Call_LTP": 50, "Put_LTP": 55, "Call_Bid": 49, "Call_Ask": 50},
            {"Strike": 25050, "Call_Vol": 180, "Put_Vol": 210, "Call_OI": 700,
             "Put_OI": 850, "Call_LTP": 30, "Put_LTP": 80, "Call_Bid": 29, "Call_Ask": 30},
        ],
        atm_strike=25000.0,
        metadata={"selected_strike": 25000.0, "instrument_consistent": True},
    )


def make_coa(snapshot_id: str, timestamp: str) -> COAResearchResult:
    return COAResearchResult.new(
        snapshot_id=snapshot_id, session_id="NIFTY:2026-07-19", experiment_id=None,
        strategy_version="COA Core v1.0", engine_version="1.0.0-baseline",
        scenario_number=1, scenario="Strong range consolidation", eos=24930.0,
        eor=25100.0, support=24950.0, resistance=25050.0, momentum=None,
        diversion=None, trend=None, direction=None, risk_mode="NORMAL_LOTS",
        raw_output={"base_strike": 25000.0}, processing_time_ms=1.0,
        market_timestamp=timestamp,
    )


class ValidationEngineTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(tempfile.mkdtemp()) / "validation.db"
        self.snapshots = initialize_snapshot_repository(str(self.db_path))
        self.coa_results = initialize_coa_result_repository(str(self.db_path))
        self.validations = initialize_validation_repository(str(self.db_path))
        self.engine = ValidationEngine()
        self.pipeline = ValidationResearchPipeline(
            self.snapshots, self.coa_results, self.validations, self.engine
        )
        self.valid = SnapshotValidationResult(True, True, 1.0)

    def tearDown(self):
        self.snapshots.connection.close()
        self.coa_results.connection.close()
        self.validations.connection.close()

    def _store_pair(self, snapshot_id: str, timestamp: str):
        snapshot = make_snapshot(snapshot_id, timestamp)
        self.snapshots.append(snapshot, self.valid)
        coa = make_coa(snapshot_id, timestamp)
        self.coa_results.append(coa)
        return snapshot, coa

    def test_each_component_is_scored_and_repeatable(self):
        snapshot, coa = self._store_pair("validation-1", "2026-07-19T09:15:00+00:00")
        record = self.snapshots.get(snapshot.snapshot_id)
        first = self.engine.evaluate(record, coa)
        second = self.engine.evaluate(record, coa)

        self.assertEqual(first.volume_score, second.volume_score)
        self.assertEqual(first.oi_score, second.oi_score)
        self.assertEqual(first.strike_score, second.strike_score)
        self.assertEqual(first.liquidity_score, second.liquidity_score)
        self.assertEqual(first.market_context_score, second.market_context_score)
        self.assertEqual(first.overall_score, second.overall_score)
        self.assertIsNone(first.historical_score)

    def test_missing_data_has_explicit_failure_or_warning(self):
        snapshot, coa = self._store_pair("validation-2", "2026-07-19T09:15:00+00:00")
        record = self.snapshots.get(snapshot.snapshot_id)
        record["option_chain"] = [{"Strike": 25000, "Call_LTP": 0, "Put_LTP": 0}]
        result = self.engine.evaluate(record, coa)

        self.assertEqual(result.volume_score, 0)
        self.assertEqual(result.oi_score, 0)
        self.assertEqual(result.liquidity_score, 0)
        self.assertTrue(result.failure_reasons)

    def test_weighted_score_bands_and_invalid_weights(self):
        scores = {"volume": 80, "open_interest": 80, "strike_quality": 80,
                  "liquidity": 80, "market_context": 80}
        self.assertEqual(weighted_score(scores, ValidationConfig().weights), 80)
        self.assertEqual(confidence_band(80), "STRONG")
        with self.assertRaises(ValueError):
            ValidationConfig(volume_weight=0.5)
        with self.assertRaises(ValueError):
            weighted_score(scores, {"volume": 1.0, "open_interest": 0.0,
                                    "strike_quality": 0.0, "liquidity": 0.0,
                                    "unexpected": 0.0})

    def test_pipeline_repository_idempotency_and_lookup(self):
        snapshot, coa = self._store_pair("validation-3", "2026-07-19T09:15:00+00:00")
        first = self.pipeline.process_coa_result_id(coa.coa_result_id, experiment_id="EXP-005")
        second = self.pipeline.process_coa_result_id(coa.coa_result_id, experiment_id="EXP-005")

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.result.validation_id, second.result.validation_id)
        self.assertEqual(len(self.validations.list_by_snapshot(snapshot.snapshot_id)), 1)
        self.assertEqual(self.validations.get(first.result.validation_id).overall_score, first.result.overall_score)

    def test_session_replay_order_and_recovery(self):
        _, first_coa = self._store_pair("validation-4a", "2026-07-19T09:15:00+00:00")
        _, second_coa = self._store_pair("validation-4b", "2026-07-19T09:16:00+00:00")
        outcomes = self.pipeline.process_session("NIFTY:2026-07-19")

        self.assertEqual([item.coa_result_id for item in outcomes],
                         [first_coa.coa_result_id, second_coa.coa_result_id])
        self.assertTrue(all(item.success for item in outcomes))

    def test_transaction_rolls_back_when_foreign_key_is_missing(self):
        result = ValidationResult.new(
            coa_result_id="missing", snapshot_id="missing", session_id="missing",
            experiment_id=None, strategy_version="test", validation_version="1.0.0",
            volume_score=1, oi_score=1, strike_score=1, liquidity_score=1,
            market_context_score=1, historical_score=None, overall_score=1,
            confidence_band="WEAK", is_valid=False, scoring_details={},
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.validations.append(result)
        count = self.validations.connection.execute(
            "SELECT COUNT(*) FROM validation_results"
        ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
