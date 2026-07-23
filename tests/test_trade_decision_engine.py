from __future__ import annotations
import os, tempfile, unittest
from src.coa.canonical import CanonicalCOAEngine
from src.decision import TradeDecisionEngine
from src.persistence import initialize_decision_repository
SNAPSHOT = {"snapshot_id":"decision-1","session_id":"session-1","market_captured_at":"2026-07-23T10:00:00+05:30","instrument":"NIFTY","spot":25020,"expiry":"2026-07-30","metadata":{"step_size":50,"available_expiries":["2026-07-30"],"call_oi_change_history":[0.0],"put_oi_change_history":[0.0]},"option_chain":[{"Strike":24950,"Call_Vol":100,"Put_Vol":300,"Call_LTP":90,"Put_LTP":25},{"Strike":25000,"Call_Vol":500,"Put_Vol":100,"Call_LTP":55,"Put_LTP":45},{"Strike":25050,"Call_Vol":300,"Put_Vol":500,"Call_LTP":30,"Put_LTP":80},{"Strike":25100,"Call_Vol":120,"Put_Vol":80,"Call_LTP":15,"Put_LTP":120}]}
class TradeDecisionEngineTests(unittest.TestCase):
    def test_rejection_is_deterministic_and_execution_is_disabled(self):
        coa = CanonicalCOAEngine().analyze(SNAPSHOT); engine = TradeDecisionEngine(); first = engine.decide(SNAPSHOT, coa, validation={"score":20}, market_quality="STALE"); second = engine.decide(SNAPSHOT, coa, validation={"score":20}, market_quality="STALE")
        self.assertEqual(first.action,"NO_TRADE"); self.assertEqual(first.quantity,0); self.assertEqual(first.metadata["execution_mode"],"DISABLED"); self.assertEqual([(r.rule,r.reason) for r in first.rejections],[(r.rule,r.reason) for r in second.rejections])
    def test_repository_records_lifecycle_and_evidence(self):
        handle,path=tempfile.mkstemp(suffix=".sqlite"); os.close(handle)
        try:
            decision=TradeDecisionEngine().decide(SNAPSHOT,CanonicalCOAEngine().analyze(SNAPSHOT),validation={"score":100}); repo=initialize_decision_repository(path); repo.append(decision)
            self.assertEqual(repo.connection.execute("SELECT COUNT(*) FROM trade_decision").fetchone()[0],1); self.assertGreater(repo.connection.execute("SELECT COUNT(*) FROM decision_evidence").fetchone()[0],0); self.assertEqual(repo.connection.execute("SELECT COUNT(*) FROM decision_lifecycle").fetchone()[0],1); repo.connection.close()
        finally: os.unlink(path)
