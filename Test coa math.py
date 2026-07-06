"""
Quick sanity tests for engine/coa_math.py — run with:  python -m pytest tests/
(or just: python tests/test_coa_math.py)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from engine.coa_math import analyze_coa_matrix_structure, compute_final_lots


def make_chain():
    return pd.DataFrame([
        {"Strike": 24300, "Call_Vol": 500000, "Call_OI": 10000, "Call_LTP": 150, "Put_LTP": 10, "Put_Vol": 300000, "Put_OI": 8000},
        {"Strike": 24350, "Call_Vol": 700000, "Call_OI": 15000, "Call_LTP": 100, "Put_LTP": 20, "Put_Vol": 500000, "Put_OI": 12000},
        {"Strike": 24400, "Call_Vol": 900000, "Call_OI": 20000, "Call_LTP": 60,  "Put_LTP": 40, "Put_Vol": 1200000, "Put_OI": 25000},
        {"Strike": 24450, "Call_Vol": 400000, "Call_OI": 9000,  "Call_LTP": 30,  "Put_LTP": 70, "Put_Vol": 600000, "Put_OI": 14000},
        {"Strike": 24500, "Call_Vol": 200000, "Call_OI": 5000,  "Call_LTP": 15,  "Put_LTP": 110, "Put_Vol": 300000, "Put_OI": 8000},
    ])


def test_support_resistance_detected():
    df = make_chain()
    result = analyze_coa_matrix_structure(df, spot=24440, step=50)
    assert result["support"] == 24400
    assert result["resistance"] == 24400
    print("support/resistance detection OK:", result["support"], result["resistance"])


def test_lot_sizing_halts_on_conflict():
    lots, permitted = compute_final_lots(4, "HALT_TRADING")
    assert lots == 0 and permitted is False
    lots, permitted = compute_final_lots(4, "NORMAL_LOTS")
    assert lots == 4 and permitted is True
    print("lot sizing OK")


if __name__ == "__main__":
    test_support_resistance_detected()
    test_lot_sizing_halts_on_conflict()
    print("All tests passed.")
