import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.coa.models import COAResearchResult
from src.persistence import (
    initialize_coa_result_repository,
    initialize_signal_repository,
    initialize_snapshot_repository,
    initialize_validation_repository,
)
from src.research.models import CapturedSnapshot
from src.research.signal_pipeline import SignalResearchPipeline
from src.research.validation import SnapshotValidationResult
from src.signal.config import SignalConfig
from src.signal.engine import SignalEngine
from src.validation.models import ValidationResult


def snapshot(snapshot_id: str, timestamp: str) -> CapturedSnapshot:
    return CapturedSnapshot(
        snapshot_id=snapshot_id, session_id="NIFTY:2026-07-19", instrument="NIFTY",
        spot=25020.0, source="test", market_captured_at=timestamp,
        ingested_at="2026-07-19T09:30:00+00:00", expiry="2026-07-23",
        option_chain=[{"Strike": 25000, "Call_LTP": 50, "Put_LTP": 55}],
    )


def coa(snapshot_id: str, timestamp: str, scenario_number: int) -> COAResearchResult:
    return COAResearchResult.new(
        snapshot_id=snapshot_id, session_id="NIFTY:2026-07-19", experiment_id=None,
        strategy_version="COA Core v1.0", engine_version="1.0.0-baseline",
        scenario_number=scenario_number, scenario="scenario-" + str(scenario_number),
        eos=24950.0, eor=25050.0, support=24950.0, resistance=25050.0,
        momentum=None, diversion=None, trend=None, direction=None, risk_mode="NORMAL_LOTS",
        raw_output={"base_strike": 25000.0}, processing_time_ms=1.0,
        market_timestamp=timestamp,
    )


def validation(coa_result: COAResearchResult, score: float = 80.0, valid: bool = True) -> ValidationResult:
    return ValidationResult.new(
        coa_result_id=coa_result.coa_result_id, snapshot_id=coa_result.snapshot_id,
        session_id=coa_result.session_id, experiment_id=None,
        strategy_version=coa_result.strategy_version, validation_version="1.0.0",
        volume_score=80.0, oi_score=80.0, strike_score=80.0, liquidity_score=80.0,
        market_context_score=80.0, historical_score=None, overall_score=score,
        confidence_band="STRONG", is_valid=valid, scoring_details={},
    )


class SignalEngineTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "signals.db"
        self.snapshots = initialize_snapshot_repository(str(self.path))
        self.coa_results = initialize_coa_result_repository(str(self.path))
        self.validations = initialize_validation_repository(str(self.path))
        self.signals = initialize_signal_repository(str(self.path))
        self.engine = SignalEngine()
        self.pipeline = SignalResearchPipeline(
            self.snapshots, self.coa_results, self.validations, self.signals, self.engine
        )
        self.capture_valid = SnapshotValidationResult(True, True, 1.0)

    def tearDown(self):
        self.snapshots.connection.close()
        self.coa_results.connection.close()
        self.validations.connection.close()
        self.signals.connection.close()

    def _store(self, signal_id: str, scenario_number: int, score: float = 80, valid: bool = True):
        snap = snapshot(signal_id, "2026-07-19T09:15:00+00:00")
        result = coa(signal_id, snap.market_captured_at, scenario_number)
        evidence = validation(result, score, valid)
        self.snapshots.append(snap, self.capture_valid)
        self.coa_results.append(result)
        self.validations.append(evidence)
        return snap, result, evidence

    def test_buy_and_sell_signal_generation(self):
        buy_snapshot, _, buy_validation = self._store("signal-buy", 5)
        sell_snapshot, _, sell_validation = self._store("signal-sell", 4)

        buy = self.pipeline.process_validation_id(buy_validation.validation_id).signal
        sell = self.pipeline.process_validation_id(sell_validation.validation_id).signal

        self.assertEqual(buy.signal_type, "BUY")
        self.assertEqual(buy.entry_price, 24950.0)
        self.assertEqual(buy.target_1, 25000.0)
        self.assertEqual(sell.signal_type, "SELL")
        self.assertEqual(sell.entry_price, 25050.0)
        self.assertEqual(sell.target_2, 24950.0)
        self.assertEqual(buy.snapshot_id, buy_snapshot.snapshot_id)
        self.assertEqual(sell.snapshot_id, sell_snapshot.snapshot_id)

    def test_no_signal_and_watchlist_explain_failures(self):
        _, _, disabled = self._store("signal-none", 1)
        _, _, weak = self._store("signal-watch", 5, score=55, valid=False)

        no_signal = self.pipeline.process_validation_id(disabled.validation_id).signal
        watchlist = self.pipeline.process_validation_id(weak.validation_id).signal

        self.assertEqual(no_signal.signal_type, "NO_SIGNAL")
        self.assertIn("no configured directional scenario applies", no_signal.reasons)
        self.assertEqual(watchlist.signal_type, "WATCHLIST")
        self.assertTrue(any("confidence" in reason for reason in watchlist.reasons))

    def test_configuration_loading_and_deterministic_values(self):
        config_path = self.path.parent / "rules.json"
        config_path.write_text(json.dumps({
            "minimum_confidence": 70, "minimum_volume_score": 60,
            "minimum_oi_score": 60, "minimum_liquidity_score": 60,
            "scenario_directions": {"5": "BUY"}, "signal_version": "test-1"
        }), encoding="utf-8")
        engine = SignalEngine(SignalConfig.from_file(config_path))
        snap, result, evidence = self._store("signal-repeat", 5, score=80)
        record = self.snapshots.get(snap.snapshot_id)

        first = engine.generate(record, result, evidence)
        second = engine.generate(record, result, evidence)
        self.assertEqual(first.deterministic_values(), second.deterministic_values())
        self.assertEqual(first.signal_version, "test-1")

    def test_repository_duplicate_protection_and_session_replay_order(self):
        _, first_coa, first_validation = self._store("signal-order-a", 5)
        _, second_coa, second_validation = self._store("signal-order-b", 4)
        first = self.pipeline.process_validation_id(first_validation.validation_id, experiment_id="EXP-006")
        duplicate = self.pipeline.process_validation_id(first_validation.validation_id, experiment_id="EXP-006")
        replay = self.pipeline.process_session("NIFTY:2026-07-19")

        self.assertEqual(first.signal.signal_id, duplicate.signal.signal_id)
        self.assertEqual(
            [outcome.signal.validation_id for outcome in replay],
            [first_validation.validation_id, second_validation.validation_id],
        )
        self.assertEqual(len(self.signals.get_snapshot_signal("signal-order-a")), 2)

    def test_foreign_key_failure_rolls_back_insert(self):
        from src.signal.models import ResearchSignal
        record = ResearchSignal.new(
            snapshot_id="missing", coa_result_id="missing", validation_id="missing",
            session_id="missing", experiment_id=None, strategy_version="test",
            signal_version="1.0.0", instrument="NIFTY", expiry=None,
            signal_type="NO_SIGNAL", signal_state="NEW", direction=None,
            entry_price=None, stop_loss=None, target_1=None, target_2=None,
            trailing_reference=None, confidence_score=0, confidence_band="WEAK",
            scenario=None, eos=None, eor=None, momentum=None, diversion=None,
            reasons=(), warnings=(), details={}, processing_time_ms=1.0,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.signals.insert_signal(record)
        self.assertEqual(
            self.signals.connection.execute("SELECT COUNT(*) FROM research_signals").fetchone()[0], 0
        )


if __name__ == "__main__":
    unittest.main()
