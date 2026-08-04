import tempfile
import unittest
from pathlib import Path

from src.application.fyers_research import FyersResearchService
from src.market_data.models import OptionChainSnapshot, OptionContract
from src.research.scenario_catalog import combined_tactical_id


def snapshot(captured_at: str, spot: float = 23767.0) -> OptionChainSnapshot:
    contracts = tuple(
        OptionContract("NIFTY", strike, "2026-07-30", side, premium, "FYERS", captured_at,
                       volume=volume, oi=oi)
        for strike, side, premium, volume, oi in (
            (23700, "CE", 120, 100, 300), (23700, "PE", 40, 220, 500),
            (23750, "CE", 85, 150, 400), (23750, "PE", 65, 180, 450),
            (23800, "CE", 55, 240, 600), (23800, "PE", 100, 90, 250),
        )
    )
    return OptionChainSnapshot.new(
        instrument_id="NIFTY", spot=spot, expiry="2026-07-30", provider="FYERS",
        captured_at=captured_at, contracts=contracts,
    )


class ScenarioShadowTests(unittest.TestCase):
    def test_unclassified_frozen_tactical_state_is_not_mislabeled_as_one_of_18(self):
        self.assertEqual(combined_tactical_id(0), 0)

    def test_every_successful_coa_snapshot_gets_one_combined_track(self):
        service = FyersResearchService(Path(tempfile.mkdtemp()) / "research.db")
        outcome = service.process(snapshot("2026-07-25T09:30:00+00:00"))
        self.assertIsNone(outcome.error)
        self.assertIsNotNone(outcome.scenario_track_id)
        track = service.latest_scenario_track("NIFTY")
        self.assertEqual(track["scenario_track_id"], outcome.scenario_track_id)
        self.assertIn(track["tactical_scenario_number"], range(10, 19))
        self.assertEqual(track["catalog_version"], "combined-18-v1")

    def test_next_session_plan_is_only_created_in_preclose_window(self):
        service = FyersResearchService(Path(tempfile.mkdtemp()) / "research.db")
        regular = service.process(snapshot("2026-07-25T08:00:00+00:00"))  # 13:30 IST
        preclose = service.process(snapshot("2026-07-25T09:30:00+00:00"))  # 15:00 IST
        self.assertIsNone(regular.trade_plan_id)
        self.assertIsNotNone(preclose.trade_plan_id)

    def test_historical_backfill_is_idempotent_and_has_no_future_lookahead(self):
        service = FyersResearchService(Path(tempfile.mkdtemp()) / "research.db")
        first = service.process(snapshot("2026-07-25T08:00:00+00:00", spot=23760.0))
        service.process(snapshot("2026-07-25T08:01:00+00:00", spot=23780.0))
        before = service.scenario_tracks.get_for_snapshot(first.snapshot_id, "combined-18-v1")
        self.assertEqual(service.backfill_scenario_tracks("NIFTY"), 2)
        after = service.scenario_tracks.get_for_snapshot(first.snapshot_id, "combined-18-v1")
        self.assertEqual(before["scenario_track_id"], after["scenario_track_id"])


if __name__ == "__main__":
    unittest.main()
