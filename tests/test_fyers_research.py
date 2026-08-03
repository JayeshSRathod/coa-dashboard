import tempfile
import unittest
from pathlib import Path

from src.application.fyers_research import FyersResearchService
from src.market_data.models import OptionChainSnapshot, OptionContract


class FyersResearchServiceTests(unittest.TestCase):
    def test_coa_snapshot_rows_preserve_provider_quote_and_oi_change_fields(self):
        contract = OptionContract(
            "NIFTY", 24000, "2026-07-30", "CE", 100, "FYERS", "2026-07-28T09:15:00+00:00",
            volume=120, oi=500, oi_change=25, iv=14.5, bid=99.5, ask=100.5,
            greeks={"delta": 0.5, "gamma": 0.02, "theta": -4.2, "vega": 8.1},
        )
        row = OptionChainSnapshot.new(
            instrument_id="NIFTY", spot=24000, expiry="2026-07-30", provider="FYERS",
            captured_at="2026-07-28T09:15:00+00:00", contracts=(contract,),
        ).coa_rows()[0]
        self.assertEqual(row["Call_Bid"], 99.5)
        self.assertEqual(row["Call_Ask"], 100.5)
        self.assertEqual(row["Call_OI_Change"], 25)
        self.assertEqual(row["Call_IV"], 14.5)
        self.assertEqual(row["Call_Delta"], 0.5)
        self.assertEqual(row["Call_Gamma"], 0.02)

    def test_live_snapshot_is_appended_then_processed_by_coa_and_validation(self):
        database = Path(tempfile.mkdtemp()) / "research.db"
        service = FyersResearchService(database)
        captured_at = "2026-07-25T09:30:00+00:00"
        contracts = tuple(
            OptionContract("NIFTY", strike, "", option_type, premium, "FYERS", captured_at, volume=volume, oi=oi)
            for strike, option_type, premium, volume, oi in (
                (23700, "CE", 120, 100, 300), (23700, "PE", 40, 220, 500),
                (23750, "CE", 85, 150, 400), (23750, "PE", 65, 180, 450),
                (23800, "CE", 55, 240, 600), (23800, "PE", 100, 90, 250),
            )
        )
        snapshot = OptionChainSnapshot.new(instrument_id="NIFTY", spot=23767.0, expiry="", provider="FYERS", captured_at=captured_at, contracts=contracts)

        outcome = service.process(snapshot)

        self.assertIsNone(outcome.error)
        self.assertIsNotNone(outcome.snapshot_id)
        self.assertIsNotNone(outcome.coa_result)
        self.assertIsNotNone(outcome.validation_result)
        self.assertIsNotNone(outcome.signal)
        self.assertIn(outcome.signal.signal_type, {"BUY", "SELL", "WATCHLIST", "NO_SIGNAL"})
        self.assertTrue(service.paper_states())
        risk = service.risk_decision_for_signal(outcome.signal)
        self.assertIsNotNone(risk)
        self.assertIn(risk.decision, {"APPROVED", "REDUCED_SIZE"})
        trade_id = str(service.paper_states()[0]["trade_id"])
        detail = service.paper_trade_detail(trade_id)
        self.assertEqual(detail["trade_id"], trade_id)
        self.assertIn("TRADE_CREATED", [event["event"] for event in detail["events"]])
        self.assertEqual(service.current_paper_trade()["trade_id"], trade_id)
        self.assertEqual(service.latest("NIFTY").snapshot_id, outcome.snapshot_id)
        self.assertIsNotNone(outcome.trade_plan_id)
        plan = service.latest_trade_plan("NIFTY")
        self.assertEqual(plan["trade_plan_id"], outcome.trade_plan_id)
        self.assertEqual(plan["planning_horizon"], "NEXT_SESSION")
        self.assertEqual(plan["evidence"]["execution_mode"] if "execution_mode" in plan["evidence"] else "PAPER_ONLY", "PAPER_ONLY")
        self.assertEqual(service.backfill_dynamic_structure("NIFTY"), 1)
        self.assertTrue(service.dynamic_events("NIFTY"))

    def test_first_snapshot_of_next_session_revalidates_prior_plan_without_broker_access(self):
        database = Path(tempfile.mkdtemp()) / "research.db"
        service = FyersResearchService(database)
        contracts = tuple(
            OptionContract("NIFTY", strike, "", option_type, premium, "FYERS", captured_at,
                           volume=volume, oi=oi)
            for strike, option_type, premium, volume, oi in (
                (23700, "CE", 120, 100, 300), (23700, "PE", 40, 220, 500),
                (23750, "CE", 85, 150, 400), (23750, "PE", 65, 180, 450),
                (23800, "CE", 55, 240, 600), (23800, "PE", 100, 90, 250),
            )
            for captured_at in ("2026-07-25T09:30:00+00:00",)
        )
        first = OptionChainSnapshot.new(
            instrument_id="NIFTY", spot=23767.0, expiry="", provider="FYERS",
            captured_at="2026-07-25T09:30:00+00:00", contracts=contracts,
        )
        first_outcome = service.process(first)
        self.assertIsNotNone(first_outcome.trade_plan_id)

        next_contracts = tuple(
            OptionContract(contract.instrument_id, contract.strike, contract.expiry, contract.option_type,
                           contract.premium, contract.provider, "2026-07-26T09:15:00+00:00",
                           volume=contract.volume, oi=contract.oi)
            for contract in contracts
        )
        second = OptionChainSnapshot.new(
            instrument_id="NIFTY", spot=23810.0, expiry="", provider="FYERS",
            captured_at="2026-07-26T09:15:00+00:00", contracts=next_contracts,
        )
        second_outcome = service.process(second)
        self.assertIsNotNone(second_outcome.premarket_validation_id)
        validation = service.latest_premarket_validation(str(first_outcome.trade_plan_id))
        self.assertEqual(validation["validation_id"], second_outcome.premarket_validation_id)
        self.assertIn(validation["validation_result"], {"VALIDATED", "MODIFIED", "CANCELLED", "OBSERVE_ONLY"})


if __name__ == "__main__":
    unittest.main()
