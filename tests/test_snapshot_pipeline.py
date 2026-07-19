from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from src.market.snapshot import MarketSnapshotPayload
from src.persistence import initialize_snapshot_repository
from src.research.collector import SnapshotCaptureService
from src.research.replay import ReplayService


def iso_at(second: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=10 - second)).isoformat()


class FakeProvider:
    def __init__(self, payloads):
        self.payloads = iter(payloads)

    def fetch_snapshot(self, instrument):
        return next(self.payloads)


class FailingProvider:
    def fetch_snapshot(self, instrument):
        raise RuntimeError("feed unavailable")


def payload(timestamp: str, spot: float = 25000.0, **overrides):
    values = {
        "instrument": "NIFTY",
        "spot": spot,
        "source": "test-feed",
        "session_id": "NIFTY:2026-07-19",
        "market_captured_at": timestamp,
        "futures_price": spot + 5,
        "atm_strike": 25000.0,
        "expiry": "2026-07-23",
        "expiry_type": "WEEKLY",
        "option_chain": [
            {
                "Strike": 25000.0,
                "Call_LTP": 100.0,
                "Put_LTP": 90.0,
                "Call_OI": 1000,
                "Put_OI": 1100,
                "Call_Vol": 500,
                "Put_Vol": 600,
            }
        ],
    }
    values.update(overrides)
    return MarketSnapshotPayload(**values)


class SnapshotPipelineTests(unittest.TestCase):
    def setUp(self):
        self.repository = initialize_snapshot_repository(
            str(Path(tempfile.mkdtemp()) / "research.db")
        )
        self.capture = SnapshotCaptureService(self.repository)

    def tearDown(self):
        self.repository.connection.close()

    def test_capture_persists_a_valid_snapshot_and_replays_in_order(self):
        first = self.capture.capture_payload(payload(iso_at(1)))
        second = self.capture.capture_payload(payload(iso_at(2), spot=25010.0))

        self.assertTrue(first.stored)
        self.assertTrue(second.stored)
        stored = self.repository.get(first.snapshot_id)
        self.assertEqual(stored["session_id"], "NIFTY:2026-07-19")
        self.assertTrue(stored["is_complete"])

        replay = ReplayService.for_session(self.repository, "NIFTY:2026-07-19")
        self.assertEqual(replay.step_forward()["snapshot_id"], first.snapshot_id)
        self.assertEqual(replay.step_forward()["snapshot_id"], second.snapshot_id)
        self.assertEqual(replay.step_backward()["snapshot_id"], first.snapshot_id)
        replay.set_playback_speed(4.0)
        self.assertEqual(replay.playback_speed, 4.0)

    def test_degraded_option_chain_is_stored_with_quality_metadata(self):
        degraded = self.capture.capture_payload(
            payload(iso_at(1), option_chain=[{"Strike": 25000.0, "Call_LTP": 100.0}])
        )
        self.assertTrue(degraded.stored)
        self.assertFalse(degraded.validation.is_complete)
        stored = self.repository.get(degraded.snapshot_id)
        self.assertEqual(stored["data_quality_status"], "DEGRADED")
        self.assertEqual(stored["missing_strikes"], [25000.0])
        self.assertEqual(len(self.repository.list_events("snapshot_degraded")), 1)

    def test_non_monotonic_snapshot_is_logged_and_not_stored(self):
        timestamp = iso_at(1)
        self.assertTrue(self.capture.capture_payload(payload(timestamp)).stored)
        rejected = self.capture.capture_payload(payload(timestamp, spot=25010.0))

        self.assertFalse(rejected.stored)
        self.assertIn("not monotonic", " ".join(rejected.validation.errors))
        self.assertEqual(len(self.repository.list_events("snapshot_validation_failed")), 1)

    def test_provider_interruption_becomes_an_event(self):
        result = self.capture.capture_from_provider(FailingProvider(), "NIFTY")
        self.assertFalse(result.stored)
        self.assertEqual(len(self.repository.list_events("feed_interruption")), 1)

    def test_provider_instrument_mismatch_is_rejected(self):
        provider = FakeProvider([payload(iso_at(1), instrument="BANKNIFTY")])
        result = self.capture.capture_from_provider(provider, "NIFTY")
        self.assertFalse(result.stored)
        self.assertIn("does not match", " ".join(result.validation.errors))


if __name__ == "__main__":
    unittest.main()
