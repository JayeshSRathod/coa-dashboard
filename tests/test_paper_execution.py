import unittest

from src.execution.config import PaperExecutionConfig
from src.execution.costs import apply_slippage, transaction_cost
from src.execution.engine import PaperExecutionEngine
from src.execution.projector import project_trade
from src.signal.models import ResearchSignal


def signal(kind="BUY"):
    return ResearchSignal.new(
        snapshot_id="s0", coa_result_id="coa", validation_id="validation", session_id="session",
        experiment_id=None, strategy_version="test", signal_version="1", instrument="NIFTY",
        expiry=None, signal_type=kind, signal_state="NEW", direction=kind if kind in {"BUY","SELL"} else None,
        entry_price=100.0 if kind in {"BUY","SELL"} else None, stop_loss=None,
        target_1=110.0 if kind in {"BUY","SELL"} else None, target_2=120.0 if kind in {"BUY","SELL"} else None,
        trailing_reference=None, confidence_score=80, confidence_band="STRONG", scenario="test",
        eos=100.0, eor=120.0, momentum=None, diversion=None, reasons=(), warnings=(), details={},
    )


def snapshot(identifier, spot, low=None, high=None, bid=9, ask=10):
    return {"snapshot_id":identifier,"market_captured_at":"2026-07-19T09:15:00+00:00",
            "spot":spot,"atm_strike":100.0,
            "metadata":{"spot_low":spot if low is None else low,"spot_high":spot if high is None else high},
            "option_chain":[{"Strike":100.0,"Call_LTP":10,"Call_Bid":bid,"Call_Ask":ask,
                             "Put_LTP":10,"Put_Bid":bid,"Put_Ask":ask}]}


class PaperExecutionTests(unittest.TestCase):
    def setUp(self):
        self.engine=PaperExecutionEngine(PaperExecutionConfig(default_quantity=10,minimum_lot_size=1))
        self.trade,self.events=self.engine.create_trade(signal(),snapshot("s0",100))

    def test_no_trade_for_no_signal(self):
        trade, events=self.engine.create_trade(signal("NO_SIGNAL"),snapshot("s0",100))
        self.assertIsNone(trade);self.assertEqual(events,[])

    def test_next_snapshot_entry_partial_exit_breakeven_and_stop(self):
        state=project_trade(self.trade,self.events)
        filled=self.engine.process_snapshot(self.trade,state,snapshot("s1",100))
        all_events=self.events+filled
        state=project_trade(self.trade,all_events)
        self.assertEqual(state.status,"OPEN")
        self.assertEqual(state.executed_entry,10)

        t1=self.engine.process_snapshot(self.trade,state,snapshot("s2",110,105,111,bid=12))
        all_events+=t1
        state=project_trade(self.trade,all_events)
        self.assertEqual(state.status,"PARTIALLY_EXITED")
        self.assertEqual(state.quantity_remaining,5)
        self.assertEqual(state.stop_loss,100.0)

        stopped=self.engine.process_snapshot(self.trade,state,snapshot("s3",99,99,105,bid=7))
        state=project_trade(self.trade,all_events+stopped)
        self.assertEqual(state.status,"CLOSED")
        self.assertEqual(state.exit_reason,"STOP_LOSS")
        self.assertTrue(state.realized_pnl != 0)

    def test_conservative_same_snapshot_uses_stop_before_target(self):
        state=project_trade(self.trade,self.events)
        all_events=self.events+self.engine.process_snapshot(self.trade,state,snapshot("s1",100))
        state=project_trade(self.trade,all_events)
        events=self.engine.process_snapshot(self.trade,state,snapshot("s2",105,95,121,bid=8))
        self.assertEqual(events[-1].payload["reason"],"STOP_LOSS")

    def test_touch_policy_and_costs_are_deterministic(self):
        engine=PaperExecutionEngine(PaperExecutionConfig(fill_policy="TOUCH_PRICE",default_quantity=1,
            fixed_slippage=1,percentage_slippage=0.01,brokerage_rate=0.001))
        trade, events=engine.create_trade(signal(),snapshot("s0",100))
        state=project_trade(trade,events)
        self.assertEqual(engine.process_snapshot(trade,state,snapshot("s1",101,99,102))[0].event_type,"ENTRY_FILLED")
        self.assertEqual(apply_slippage(10,is_entry=True,config=engine.config),11.1)
        self.assertGreater(transaction_cost(10,1,engine.config),0)

    def test_projector_reconstructs_identical_state(self):
        state=project_trade(self.trade,self.events)
        events=self.engine.process_snapshot(self.trade,state,snapshot("s1",100))
        first=project_trade(self.trade,self.events+events)
        second=project_trade(self.trade,list(self.events+events))
        self.assertEqual(first,second)


if __name__=="__main__":
    unittest.main()
