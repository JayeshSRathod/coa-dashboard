"""
Quick sanity tests for engine/coa_math.py — run with:  python -m pytest tests/
(or just: python tests/test_coa_math.py)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from engine.coa_math import analyze_coa_matrix_structure, compute_final_lots, smooth_bias, _side_analysis


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


def test_eos_eor_inputs_are_exposed():
    df = make_chain()
    result = analyze_coa_matrix_structure(df, spot=24440, step=50)
    assert "atm_call_ltp" in result and "atm_put_ltp" in result and "avg_premium" in result
    assert result["avg_premium"] == (result["atm_call_ltp"] + result["atm_put_ltp"]) / 2
    print("EOS/EOR raw inputs exposed OK")


def test_select_otm_strike_matches_worked_example():
    from engine.coa_math import select_otm_strike
    # Directly from the spec's own worked example: EOS=24,062.25 -> buy 24,100 CE;
    # EOR=24,188.50 -> buy 24,150 PE. Naive "nearest strike" rounding gives
    # 24,050 and 24,200 instead — wrong. This test locks in the verified rule.
    assert select_otm_strike(24062.25, 50, "CE") == 24100
    assert select_otm_strike(24188.50, 50, "PE") == 24150
    print("OTM strike selection matches documented worked example OK")


def test_select_otm_strike_ceiling_and_floor_directions():
    from engine.coa_math import select_otm_strike
    # Exact multiple of step should return itself in both directions.
    assert select_otm_strike(24400.0, 50, "CE") == 24400
    assert select_otm_strike(24400.0, 50, "PE") == 24400
    # Different step sizes (e.g. BANK NIFTY/SENSEX at 100) should scale correctly.
    assert select_otm_strike(51835.0, 100, "CE") == 51900
    assert select_otm_strike(51835.0, 100, "PE") == 51800
    print("OTM strike ceiling/floor directions correct across step sizes OK")


def test_range_target_is_midpoint():
    from engine.coa_math import compute_range_target
    assert compute_range_target(eos=24380, eor=24500) == 24440.0
    print("range target (midpoint) OK")


def test_choose_t1_prefers_valid_diversion_over_fallback():
    from engine.coa_math import choose_t1_target
    # CALL trade: entry 24380, fallback (range midpoint) 24440.
    # A diversion pivot at 24410 sits between them -> should be preferred.
    result = choose_t1_target(entry=24380, fallback_target=24440, candidates=[24410, None], direction="up")
    assert result == 24410
    print("diversion preferred over fallback when valid OK")


def test_choose_t1_falls_back_when_no_valid_diversion():
    from engine.coa_math import choose_t1_target
    # Diversion at 24460 is PAST the fallback target (24440) — not valid for an "up" trade.
    result = choose_t1_target(entry=24380, fallback_target=24440, candidates=[24460], direction="up")
    assert result == 24440
    print("fallback used when diversion is out of range OK")


def test_choose_t1_picks_nearer_of_two_valid_diversions():
    from engine.coa_math import choose_t1_target
    result = choose_t1_target(entry=24380, fallback_target=24440, candidates=[24430, 24400], direction="up")
    assert result == 24400  # closer to entry than 24430
    print("nearer valid diversion chosen over farther one OK")


def test_choose_t1_works_for_put_direction():
    from engine.coa_math import choose_t1_target
    # PUT trade: entry 24500 (EOR), fallback (range midpoint) 24440.
    # Diversion at 24470 sits between them in the falling direction.
    result = choose_t1_target(entry=24500, fallback_target=24440, candidates=[24470], direction="down")
    assert result == 24470
    print("diversion-aware T1 works for PUT direction OK")


def test_eos_eor_alt_uses_primary_strikes_own_ltp():
    df = make_chain()
    result = analyze_coa_matrix_structure(df, spot=24440, step=50)
    # Support strike is 24400, whose own Put_LTP in make_chain() is 40.
    # Resistance strike is 24400, whose own Call_LTP in make_chain() is 60.
    expected_eos_alt = result["support"] - 40  # Put_LTP at strike 24400
    expected_eor_alt = result["resistance"] + 60  # Call_LTP at strike 24400
    assert result["eos_alt"] == expected_eos_alt
    assert result["eor_alt"] == expected_eor_alt
    # The two methods should generally differ, since ATM straddle average
    # and the primary strike's own LTP aren't the same input in general.
    print(f"alt EOS/EOR OK: eos={result['eos']:.2f} vs eos_alt={result['eos_alt']:.2f}, "
          f"eor={result['eor']:.2f} vs eor_alt={result['eor_alt']:.2f}")


def test_pressure_detected_beyond_rank_two():
    # Primary wall at 24400 (900k). Rank-2 (24450, 400k) alone is under 80% of
    # primary (44%) so old rank-2-only logic would call this a STRONG WALL.
    # But rank-2 + rank-3 + rank-4 combined (400k+300k+200k=900k) equals the
    # primary itself — real collective pressure the old logic couldn't see.
    scan_df = pd.DataFrame([
        {"Strike": 24400, "Call_Vol": 900000},
        {"Strike": 24450, "Call_Vol": 400000},
        {"Strike": 24500, "Call_Vol": 300000},
        {"Strike": 24550, "Call_Vol": 200000},
    ])
    primary_strike, state, strength, bias = _side_analysis(scan_df, "Call_Vol", scan_df, top_n=4)
    assert primary_strike == 24400
    assert strength >= 0.80, f"Expected combined pressure >= 80%, got {strength:.2f}"
    assert bias == "BULLISH", "Combined pressure sits above the wall, should read bullish (WTT)"
    print(f"top-N pressure detection OK: strength={strength:.2f}, bias={bias}")


def test_rank_two_alone_still_works_as_before():
    # Sanity check: a simple two-node case should behave the same as the old
    # rank-2-only logic did.
    scan_df = pd.DataFrame([
        {"Strike": 24400, "Call_Vol": 1000000},
        {"Strike": 24450, "Call_Vol": 900000},
    ])
    primary_strike, state, strength, bias = _side_analysis(scan_df, "Call_Vol", scan_df, top_n=4)
    assert strength == 0.9
    assert bias == "BULLISH"
    print("simple rank-2 case still works OK")


def test_smooth_bias_requires_persistence():
    # A single blip shouldn't flip the confirmed trend.
    history = ["STABLE", "BEARISH"]
    assert smooth_bias(history, min_persistence=2) == "STABLE"
    print("single blip correctly ignored OK")


def test_smooth_bias_confirms_after_persistence():
    # Two consecutive identical readings should confirm the new trend.
    history = ["STABLE", "BEARISH", "BEARISH"]
    assert smooth_bias(history, min_persistence=2) == "BEARISH"
    print("persistent trend correctly confirmed OK")


def test_smooth_bias_holds_through_oscillation():
    # Bouncing between two states every poll should never confirm either —
    # this is the "pulls up and down" scenario the user asked about.
    history = ["STABLE", "BULLISH", "STABLE", "BULLISH", "STABLE"]
    result = smooth_bias(history, min_persistence=2)
    assert result == "STABLE", f"Expected to hold last confirmed value, got {result}"
    print("oscillation correctly does not flip the confirmed trend OK")


def make_biased_chain(sup_bias: str, res_bias: str):
    """
    Builds a chain engineered to produce the requested (support_bias,
    resistance_bias) combination, so all 9 documented scenarios can be
    tested directly rather than relying on incidental chain shapes.

    Support (put side) scans Strike <= strike_above; primary wall placed at
    base_strike (24400) with room for a lower (24350) or higher (24450)
    secondary node, both within that window.

    Resistance (call side) scans Strike >= base_strike; primary wall placed
    at strike_above (24450) with room for a lower (24400) or higher (24500)
    secondary node, both within that window.
    """
    strikes = [24300, 24350, 24400, 24450, 24500, 24550]
    call_vol = {s: 10000 for s in strikes}
    put_vol = {s: 10000 for s in strikes}

    put_vol[24400] = 1000000  # support primary
    call_vol[24450] = 1000000  # resistance primary

    put_secondary_strike = 24350 if sup_bias == "BEARISH" else 24450
    call_secondary_strike = 24400 if res_bias == "BEARISH" else 24500

    if sup_bias != "STABLE":
        put_vol[put_secondary_strike] = 900000
    if res_bias != "STABLE":
        call_vol[call_secondary_strike] = 900000

    return pd.DataFrame([
        {"Strike": s, "Call_Vol": call_vol[s], "Put_Vol": put_vol[s],
         "Call_OI": 1000, "Put_OI": 1000, "Call_LTP": 50.0, "Put_LTP": 50.0}
        for s in strikes
    ])


EXPECTED_SCENARIOS = {
    ("STABLE", "STABLE"):  (1, "NORMAL_LOTS"),
    ("STABLE", "BEARISH"): (2, "REDUCED_LOTS"),
    ("STABLE", "BULLISH"): (3, "REDUCED_LOTS"),
    ("BEARISH", "STABLE"): (4, "REDUCED_LOTS"),
    ("BULLISH", "STABLE"): (5, "REDUCED_LOTS"),
    ("BEARISH", "BEARISH"): (6, "SCALE_DOWN"),
    ("BULLISH", "BULLISH"): (7, "SCALE_DOWN"),
    ("BULLISH", "BEARISH"): (8, "HALT_TRADING"),
    ("BEARISH", "BULLISH"): (9, "HALT_TRADING"),
}


def test_all_nine_scenarios_are_distinct_and_correct():
    """
    This is the test that would have caught the original bug: Scenarios 3
    and 4 (support/resistance combos that are genuinely tradeable per the
    theory) were previously falling into a catch-all HALT_TRADING branch.
    """
    for (sup_bias, res_bias), (expected_num, expected_risk) in EXPECTED_SCENARIOS.items():
        df = make_biased_chain(sup_bias, res_bias)
        result = analyze_coa_matrix_structure(df, spot=24425, step=50)
        assert result["support_bias"] == sup_bias, (
            f"Expected support_bias={sup_bias}, got {result['support_bias']}"
        )
        assert result["resistance_bias"] == res_bias, (
            f"Expected resistance_bias={res_bias}, got {result['resistance_bias']}"
        )
        assert result["scenario_number"] == expected_num, (
            f"({sup_bias},{res_bias}): expected scenario {expected_num}, got {result['scenario_number']}"
        )
        assert result["risk_mode"] == expected_risk, (
            f"Scenario {expected_num}: expected risk_mode {expected_risk}, got {result['risk_mode']}"
        )
    print("All 9 documented COA scenarios map correctly — no catch-all bug.")


def test_scenarios_3_and_4_are_not_halted():
    """Directly targets the reported bug: these must NOT be HALT_TRADING."""
    df3 = make_biased_chain("STABLE", "BULLISH")
    result3 = analyze_coa_matrix_structure(df3, spot=24425, step=50)
    assert result3["risk_mode"] != "HALT_TRADING", "Scenario 3 wrongly halted"
    assert result3["scenario_number"] == 3

    df4 = make_biased_chain("BEARISH", "STABLE")
    result4 = analyze_coa_matrix_structure(df4, spot=24425, step=50)
    assert result4["risk_mode"] != "HALT_TRADING", "Scenario 4 wrongly halted"
    assert result4["scenario_number"] == 4
    print("Scenarios 3 and 4 correctly remain tradeable, not halted OK")


if __name__ == "__main__":
    test_support_resistance_detected()
    test_lot_sizing_halts_on_conflict()
    test_eos_eor_inputs_are_exposed()
    test_select_otm_strike_matches_worked_example()
    test_select_otm_strike_ceiling_and_floor_directions()
    test_range_target_is_midpoint()
    test_choose_t1_prefers_valid_diversion_over_fallback()
    test_choose_t1_falls_back_when_no_valid_diversion()
    test_choose_t1_picks_nearer_of_two_valid_diversions()
    test_choose_t1_works_for_put_direction()
    test_eos_eor_alt_uses_primary_strikes_own_ltp()
    test_pressure_detected_beyond_rank_two()
    test_rank_two_alone_still_works_as_before()
    test_smooth_bias_requires_persistence()
    test_smooth_bias_confirms_after_persistence()
    test_smooth_bias_holds_through_oscillation()
    test_all_nine_scenarios_are_distinct_and_correct()
    test_scenarios_3_and_4_are_not_halted()
    print("All tests passed.")
