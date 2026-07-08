import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.instruments import INSTRUMENTS

# These values were pulled directly from Dhan's published instrument master
# (https://images.dhan.co/api-data/api-scrip-master.csv) on 2026-07-07 —
# not guessed. If Dhan ever changes these, this test should be the thing
# that catches drift, not a silently wrong live trade.
EXPECTED = {
    "NIFTY 50": (13, "IDX_I"),
    "BANK NIFTY": (25, "IDX_I"),
    "FINNIFTY": (27, "IDX_I"),
    "SENSEX": (51, "IDX_I"),
}


def test_security_ids_match_verified_values():
    for name, (expected_id, expected_seg) in EXPECTED.items():
        cfg = INSTRUMENTS[name]
        assert cfg["security_id"] == expected_id, f"{name}: expected id {expected_id}, got {cfg['security_id']}"
        assert cfg["dhan_segment"] == expected_seg, f"{name}: expected segment {expected_seg}, got {cfg['dhan_segment']}"
    print("All instrument security IDs match verified values.")


if __name__ == "__main__":
    test_security_ids_match_verified_values()
