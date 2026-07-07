"""
Momentum Scoring
-----------------
Combines several signals into a single comparable "momentum score" per
instrument, so multiple indices can be ranked against each other in a
leaderboard. This is a relative-ranking heuristic, not a trading signal —
it tells you where the most is happening right now, not what to do about it.

Components (each computed as a % or point change since the last poll):
  - roc            : underlying price rate-of-change
  - oi_change_pct  : change in total chain OI (fresh positions vs unwinding)
  - vol_change_pct : change in total chain volume
  - ratio_velocity : change in the stronger side's WTT/WTB ratio (percentage points)

The composite score weights price movement most heavily, since that's the
most directly observable signal, with OI/volume/ratio changes as
supporting context.
"""


def compute_totals(chain_df) -> dict:
    """Aggregate chain-wide totals used as the momentum baseline."""
    return {
        "total_call_vol": float(chain_df["Call_Vol"].sum()),
        "total_put_vol": float(chain_df["Put_Vol"].sum()),
        "total_oi": float((chain_df["Call_OI"] + chain_df["Put_OI"]).sum()),
    }


def compute_momentum(metrics: dict, totals: dict, prev_snapshot: dict | None, spot: float) -> dict:
    """
    Returns component deltas + a composite score for one instrument.
    prev_snapshot is None on the first poll for that instrument — score is 0
    until there's a prior point to compare against.
    """
    if prev_snapshot is None:
        return {
            "roc": 0.0, "oi_change_pct": 0.0, "vol_change_pct": 0.0,
            "ratio_velocity": 0.0, "score": 0.0,
        }

    prev_spot = prev_snapshot.get("spot", spot) or spot
    roc = ((spot - prev_spot) / prev_spot * 100) if prev_spot else 0.0

    prev_oi = prev_snapshot.get("total_oi", totals["total_oi"]) or 1
    oi_change_pct = ((totals["total_oi"] - prev_oi) / prev_oi) * 100

    prev_vol = (prev_snapshot.get("total_call_vol", 0) + prev_snapshot.get("total_put_vol", 0)) or 1
    cur_vol = totals["total_call_vol"] + totals["total_put_vol"]
    vol_change_pct = ((cur_vol - prev_vol) / prev_vol) * 100

    ratio_now = max(metrics["resistance_ratio"], metrics["support_ratio"])
    ratio_prev = prev_snapshot.get("ratio", ratio_now)
    ratio_velocity = (ratio_now - ratio_prev) * 100  # convert fraction to percentage points

    score = (abs(roc) * 2.0) + (abs(oi_change_pct) * 0.5) + (abs(vol_change_pct) * 0.3) + (abs(ratio_velocity) * 0.5)

    return {
        "roc": round(roc, 3),
        "oi_change_pct": round(oi_change_pct, 2),
        "vol_change_pct": round(vol_change_pct, 2),
        "ratio_velocity": round(ratio_velocity, 2),
        "score": round(score, 2),
    }


def make_snapshot(metrics: dict, totals: dict, spot: float) -> dict:
    """Snapshot to store for next poll's comparison."""
    return {
        "spot": spot,
        "total_oi": totals["total_oi"],
        "total_call_vol": totals["total_call_vol"],
        "total_put_vol": totals["total_put_vol"],
        "ratio": max(metrics["resistance_ratio"], metrics["support_ratio"]),
    }
