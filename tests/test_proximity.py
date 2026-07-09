import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.proximity import check_proximity


def test_near_eos_within_threshold():
    result = check_proximity(spot=24398, eos=24400, eor=24500)
    assert result["near_eos"] is True
    assert result["near_eor"] is False
    print("near EOS detection OK")


def test_near_eor_within_threshold():
    result = check_proximity(spot=24497, eos=24400, eor=24500)
    assert result["near_eor"] is True
    assert result["near_eos"] is False
    print("near EOR detection OK")


def test_not_near_either():
    result = check_proximity(spot=24450, eos=24400, eor=24500)
    assert result["near_eos"] is False and result["near_eor"] is False
    print("far from both correctly not flagged OK")


def test_exact_threshold_boundary_counts_as_near():
    result = check_proximity(spot=24395, eos=24400, eor=24500, threshold=5.0)
    assert result["near_eos"] is True  # exactly 5 points away
    print("exact threshold boundary counts as near OK")


if __name__ == "__main__":
    test_near_eos_within_threshold()
    test_near_eor_within_threshold()
    test_not_near_either()
    test_exact_threshold_boundary_counts_as_near()
    print("All proximity tests passed.")
