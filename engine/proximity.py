"""
Proximity Alerts
------------------
Per the production spec: "When spot approaches within +/-5 points of EOS or
EOR, the target coordinate flashes to prompt the user's focus."

Pure function — caller (app.py) tracks transition state in session state so
alerts fire once per approach, not on every rerun while sitting near the level.
"""


def check_proximity(spot: float, eos: float, eor: float, threshold: float = 5.0) -> dict:
    dist_to_eos = abs(spot - eos)
    dist_to_eor = abs(spot - eor)
    return {
        "near_eos": dist_to_eos <= threshold,
        "near_eor": dist_to_eor <= threshold,
        "dist_to_eos": dist_to_eos,
        "dist_to_eor": dist_to_eor,
    }
