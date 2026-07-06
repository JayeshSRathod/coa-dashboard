"""
Data Feed
---------
generate_simulated_chain() produces a realistic-looking option chain for
local development and testing without needing live broker credentials.

To go live: replace the body of get_option_chain() with a real DhanHQ call
(dhanhq.get_option_chain / WebSocket subscription) that returns a DataFrame
with the same columns: Strike, Call_OI, Call_Vol, Call_LTP, Put_LTP, Put_Vol, Put_OI
"""

import pandas as pd


def generate_simulated_chain(spot: float, step: int) -> pd.DataFrame:
    """Simulates a realistic option chain snapshot around the given spot."""
    strikes = [int((spot // step) * step + (i * step)) for i in range(-6, 7)]
    records = []
    base_strike = (spot // step) * step

    for s in strikes:
        dist = abs(spot - s)
        c_v = int(max(15000, 4_800_000 - (dist * 40000))) if s >= spot else int(5_500_000 - (dist * 25000))
        p_v = int(max(15000, 4_800_000 - (dist * 40000))) if s <= spot else int(5_500_000 - (dist * 25000))

        # Inject a deliberate secondary node so WTT/WTB vectors have something to detect
        if s == int(base_strike + step):
            c_v = int(c_v * 1.38)
        if s == int(base_strike - step):
            p_v = int(p_v * 1.15)

        c_v = max(c_v, 1)
        p_v = max(p_v, 1)

        records.append({
            "Strike": s,
            "Call_OI": int(c_v / 30),
            "Call_Vol": c_v,
            "Call_LTP": round(max(4.0, 140 - (s - spot) * 0.65) if s > spot else max(4.0, spot - s + 45), 2),
            "Put_LTP": round(max(4.0, 140 - (spot - s) * 0.65) if s < spot else max(4.0, s - spot + 45), 2),
            "Put_Vol": p_v,
            "Put_OI": int(p_v / 30),
        })

    return pd.DataFrame(records)


def get_option_chain(index_ticker: str, spot: float, step: int) -> pd.DataFrame:
    """
    Single entry point the dashboard calls every poll.
    Swap this body for a real DhanHQ API call when going live —
    the rest of the app never needs to change.
    """
    return generate_simulated_chain(spot, step)
