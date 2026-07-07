import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from engine.momentum import compute_totals, compute_momentum, make_snapshot, compute_hottest_strike


def make_chain(call_vol=1000, put_vol=1000, oi=500):
    return pd.DataFrame([
        {"Strike": 24300, "Call_Vol": call_vol, "Put_Vol": put_vol, "Call_OI": oi, "Put_OI": oi},
        {"Strike": 24350, "Call_Vol": call_vol, "Put_Vol": put_vol, "Call_OI": oi, "Put_OI": oi},
    ])


def test_hottest_strike_picks_max_cell():
    df = pd.DataFrame([
        {"Strike": 24300, "Call_Vol": 500000, "Put_Vol": 200000, "Call_OI": 1000, "Put_OI": 800},
        {"Strike": 24350, "Call_Vol": 300000, "Put_Vol": 900000, "Call_OI": 700, "Put_OI": 2200},
    ])
    hottest = compute_hottest_strike(df)
    assert hottest["strike"] == 24350
    assert hottest["type"] == "PE"
    assert hottest["volume"] == 900000
    print("hottest strike detection OK:", hottest)


def test_first_poll_scores_zero():
    totals = compute_totals(make_chain())
    metrics = {"resistance_ratio": 0.5, "support_ratio": 0.3}
    result = compute_momentum(metrics, totals, prev_snapshot=None, spot=24400)
    assert result["score"] == 0.0
    print("first poll -> score 0 OK")


def test_price_move_increases_score():
    metrics = {"resistance_ratio": 0.5, "support_ratio": 0.3}
    chain = make_chain()
    totals = compute_totals(chain)
    prev = make_snapshot(metrics, totals, spot=24400)
    result = compute_momentum(metrics, totals, prev, spot=24500)  # +100 pts moved
    assert result["roc"] > 0
    assert result["score"] > 0
    print("price move -> score > 0 OK:", result)


def test_higher_move_scores_higher():
    metrics = {"resistance_ratio": 0.5, "support_ratio": 0.3}
    chain = make_chain()
    totals = compute_totals(chain)
    prev = make_snapshot(metrics, totals, spot=24400)
    small = compute_momentum(metrics, totals, prev, spot=24420)
    big = compute_momentum(metrics, totals, prev, spot=24700)
    assert big["score"] > small["score"]
    print("bigger move -> higher score OK")


if __name__ == "__main__":
    test_first_poll_scores_zero()
    test_price_move_increases_score()
    test_higher_move_scores_higher()
    test_hottest_strike_picks_max_cell()
    print("All momentum tests passed.")
