import sys
import os
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.coa2_momentum import (
    compute_side_oi_change_pct, classify_line_state, classify_tactical_scenario,
)


def test_oi_change_pct_basic():
    assert compute_side_oi_change_pct(110, 100) == 10.0
    assert compute_side_oi_change_pct(90, 100) == -10.0
    assert compute_side_oi_change_pct(100, 0) == 0.0  # no prior baseline
    print("OI change % calculation OK")


def test_classify_stable_on_small_moves():
    history = [1.0, -1.5, 2.0]
    assert classify_line_state(history) == "STABLE"
    print("small moves classified STABLE OK")


def test_classify_screaming_up_fixed_threshold():
    history = [2.0, 3.0, 20.0]  # 20% jump exceeds fixed 15% threshold
    assert classify_line_state(history) == "SCREAMING_UP"
    print("fixed-threshold screaming-up detection OK")


def test_classify_fleeing_down_fixed_threshold():
    history = [1.0, -2.0, -18.0]
    assert classify_line_state(history) == "FLEEING_DOWN"
    print("fixed-threshold fleeing-down detection OK")


def test_classify_screaming_relative_to_own_average():
    # Small in absolute terms (8%) but this line's own recent average is tiny
    # (~0.9%), so 8% is ~9x its own baseline — should still trigger even
    # though it's nowhere near the fixed 15% threshold.
    history = [0.5, 1.0, 1.2, 8.0]
    assert classify_line_state(history, fixed_threshold=15.0, relative_multiplier=3.0) == "SCREAMING_UP"
    print("relative-to-own-average screaming detection OK")


def test_classify_volatile_on_sign_flips():
    history = [5.0, -6.0, 7.0]  # alternating sign, all above noise floor
    assert classify_line_state(history) == "VOLATILE"
    print("volatile/choppy detection OK")


def test_scenario_1_both_flat():
    result = classify_tactical_scenario("STABLE", "STABLE", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 1
    print("scenario 1 (both flat) OK")


def test_scenario_2_call_screaming_put_stable():
    result = classify_tactical_scenario("SCREAMING_UP", "STABLE", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 2 and result["action"] == "SELL"
    print("scenario 2 (call screaming, put stable) OK")


def test_scenario_3_capitulation():
    result = classify_tactical_scenario("SCREAMING_UP", "FLEEING_DOWN", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 3 and result["action"] == "SHORT"
    print("scenario 3 (capitulation) OK")


def test_scenario_6_short_squeeze():
    result = classify_tactical_scenario("FLEEING_DOWN", "SCREAMING_UP", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 6 and result["action"] == "BUY_AGGRESSIVE"
    print("scenario 6 (short squeeze) OK")


def test_scenario_7_erratic_call():
    result = classify_tactical_scenario("VOLATILE", "FLEEING_DOWN", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 7 and result["action"] == "SELL_RALLIES"
    print("scenario 7 (erratic call, put fleeing) OK")


def test_scenario_8_morning_race_only_in_window():
    in_window = classify_tactical_scenario("SCREAMING_UP", "SCREAMING_UP",
                                            now=datetime.datetime(2026, 7, 8, 9, 20))
    assert in_window["number"] == 8 and in_window["action"] == "WAIT"
    assert "9:15" in in_window["dynamics"] or "race" in in_window["name"].lower()

    outside_window = classify_tactical_scenario("SCREAMING_UP", "SCREAMING_UP",
                                                 now=datetime.datetime(2026, 7, 8, 13, 0))
    assert outside_window["number"] == 8
    assert "outside" in outside_window["name"].lower()
    print("scenario 8 (morning race) correctly time-gated OK")


def test_scenario_9_squareoff_only_after_310pm():
    in_window = classify_tactical_scenario("FLEEING_DOWN", "FLEEING_DOWN",
                                            now=datetime.datetime(2026, 7, 8, 15, 20))
    assert in_window["number"] == 9 and in_window["action"] == "STAND_ASIDE"

    outside_window = classify_tactical_scenario("FLEEING_DOWN", "FLEEING_DOWN",
                                                 now=datetime.datetime(2026, 7, 8, 11, 0))
    assert outside_window["number"] == 9
    assert "outside" in outside_window["name"].lower()
    print("scenario 9 (squaring-off) correctly time-gated OK")


def test_no_clean_match_falls_back_gracefully():
    result = classify_tactical_scenario("VOLATILE", "STABLE", now=datetime.datetime(2026, 7, 8, 11, 0))
    assert result["number"] == 0 and result["action"] == "WAIT"
    print("unmatched combination falls back to WAIT, not a crash OK")


if __name__ == "__main__":
    test_oi_change_pct_basic()
    test_classify_stable_on_small_moves()
    test_classify_screaming_up_fixed_threshold()
    test_classify_fleeing_down_fixed_threshold()
    test_classify_screaming_relative_to_own_average()
    test_classify_volatile_on_sign_flips()
    test_scenario_1_both_flat()
    test_scenario_2_call_screaming_put_stable()
    test_scenario_3_capitulation()
    test_scenario_6_short_squeeze()
    test_scenario_7_erratic_call()
    test_scenario_8_morning_race_only_in_window()
    test_scenario_9_squareoff_only_after_310pm()
    test_no_clean_match_falls_back_gracefully()
    print("All COA 2.0 tests passed.")
