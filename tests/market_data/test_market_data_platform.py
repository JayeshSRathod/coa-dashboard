from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.market_data.api import MarketReadService
from src.market_data.contracts import OptionChainRequest
from src.market_data.mappers.dhan_mapper import map_dhan_option_chain
from src.market_data.mappers.fyers_mapper import map_fyers_option_chain
from src.market_data.models import CircuitState, OptionChainSnapshot, ProviderHealth, QualityState
from src.market_data.provider_router import MarketDataRouter
from src.market_data.quality import MarketDataQualityEngine
from src.market_data.snapshot_service import MarketDataSnapshotService
from src.persistence import initialize_market_data_repository, initialize_snapshot_repository
from src.research.collector import SnapshotCaptureService


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def chain(provider: str = "TEST", captured_at: str | None = None) -> OptionChainSnapshot:
    raw = {"last_price": 25000, "oc": {"25000": {"ce": {"last_price": 100, "oi": 1000, "volume": 500}, "pe": {"last_price": 90, "oi": 1100, "volume": 600}}}}
    snapshot = map_dhan_option_chain(raw, instrument_id="NIFTY", expiry="2026-07-23", captured_at=captured_at or now())
    return OptionChainSnapshot(snapshot.snapshot_id, snapshot.instrument_id, snapshot.spot, snapshot.expiry, provider, snapshot.captured_at, snapshot.contracts, latency_ms=12)


class FakeProvider:
    def __init__(self, name: str, snapshot: OptionChainSnapshot | None = None, error: Exception | None = None):
        self.name, self.snapshot, self.error = name, snapshot, error
        self._health = ProviderHealth(name, now(), QualityState.HEALTHY, 1, 0, now(), CircuitState.CLOSED)

    def fetch_option_chain(self, request):
        if self.error:
            raise self.error
        return self.snapshot

    def fetch_quote(self, instrument_id, symbol):
        raise NotImplementedError

    def health(self):
        return self._health


class MarketDataPlatformTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        database = str(Path(self.directory.name) / "market.db")
        self.repository = initialize_market_data_repository(database)
        self.legacy_repository = initialize_snapshot_repository(database)

    def tearDown(self):
        self.repository.connection.close()
        self.legacy_repository.connection.close()
        self.directory.cleanup()

    def test_broker_mappers_emit_identical_cqrp_contract_shape(self):
        fyers = map_fyers_option_chain({"optionsChain": [{"ltp": 25000}, {"option_type": "CE", "strike_price": 25000, "ltp": 100, "oi": 1000, "volume": 500}, {"option_type": "PE", "strike_price": 25000, "ltp": 90, "oi": 1100, "volume": 600}]}, instrument_id="NIFTY", expiry="2026-07-23", captured_at=now())
        dhan = map_dhan_option_chain({"last_price": 25000, "oc": {"25000": {"ce": {"last_price": 100, "oi": 1000, "volume": 500}, "pe": {"last_price": 90, "oi": 1100, "volume": 600}}}}, instrument_id="NIFTY", expiry="2026-07-23", captured_at=now())
        self.assertEqual(fyers.coa_rows(), dhan.coa_rows())
        self.assertEqual(len(fyers.contracts), 2)
        self.assertEqual(len(dhan.contracts), 2)

    def test_router_records_explicit_provider_transition(self):
        transitions = []
        router = MarketDataRouter((FakeProvider("FYERS", error=RuntimeError("offline")), FakeProvider("DHAN", chain("DHAN"))), transitions.append)
        result = router.fetch_option_chain(OptionChainRequest("NIFTY", "NIFTY", "2026-07-23", security_id=13, segment="IDX_I"))
        self.assertEqual(result.provider, "DHAN")
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].reason, "fallback_after_provider_failure")

    def test_quality_blocks_stale_and_incomplete_decision_path(self):
        stale = chain(captured_at=(datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat())
        assessment = MarketDataQualityEngine(max_age_seconds=15).assess(stale)
        self.assertEqual(assessment.state, QualityState.STALE)
        self.assertFalse(assessment.decision_allowed)

    def test_snapshot_service_persists_canonical_and_replay_compatible_records(self):
        snapshot = chain("DHAN")
        router = MarketDataRouter((FakeProvider("DHAN", snapshot),), self.repository.append_transition, self.repository.append_health)
        service = MarketDataSnapshotService(router, self.repository, replay_capture=SnapshotCaptureService(self.legacy_repository))
        result = service.capture(OptionChainRequest("NIFTY", "NIFTY", "2026-07-23", security_id=13, segment="IDX_I"))
        self.assertTrue(result.decision_allowed)
        self.assertTrue(result.legacy_capture.stored)
        replay = service.replay("NIFTY")
        self.assertEqual(replay[0]["snapshot_id"], result.snapshot_id)
        self.assertEqual(replay[0]["payload"]["provider"], "DHAN")
        self.assertEqual(len(self.repository.latest_health()), 1)
        self.assertEqual(self.repository.list_transitions("NIFTY")[0]["to_provider"], "DHAN")

    def test_read_api_is_read_only_and_serializable(self):
        self.repository.append_snapshot(chain("DHAN"))
        api = MarketReadService(self.repository)
        self.assertEqual(api.system()["execution_mode"], "DISABLED")
        self.assertTrue(api.system()["read_only"])
        self.assertEqual(api.market("NIFTY")["snapshot"]["provider"], "DHAN")


if __name__ == "__main__":
    unittest.main()
