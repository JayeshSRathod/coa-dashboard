"""
COA Mathematical Core
----------------------
Implements the Chart of Accuracy structural analysis:
  - Support / Resistance wall detection (max Volume/OI strike)
  - WTT / WTB directional vectors (top-N pressure window, not just rank-2)
  - EOS / EOR entry level calculation
  - Scenario classification + risk sizing mode

This module is pure logic (no Streamlit, no I/O) so it can be unit tested
independently of the dashboard.
"""

import math
import pandas as pd


def _side_analysis(df: pd.DataFrame, vol_col: str, scan_df: pd.DataFrame, top_n: int = 4):
    """
    Shared logic for one side of the chain (calls or puts).

    Looks at a WINDOW of the top `top_n` nodes, not just the single
    second-largest — this catches pressure building at 3rd/4th rank that a
    strict rank-2 comparison would miss entirely. Direction is the
    volume-weighted centroid of the non-primary nodes in that window;
    magnitude is their combined volume relative to the primary wall.

    Returns (primary_strike, state_label, strength_ratio, bias).
    """
    idx_primary = scan_df[vol_col].idxmax()
    primary_strike = scan_df.loc[idx_primary, "Strike"]

    sorted_df = scan_df.sort_values(by=vol_col, ascending=False).reset_index(drop=True)
    primary_vol = sorted_df.loc[0, vol_col]
    window = sorted_df.iloc[:min(top_n, len(sorted_df))]
    other_nodes = window.iloc[1:]

    if len(other_nodes) > 0 and primary_vol > 0:
        strength = other_nodes[vol_col].sum() / primary_vol
    else:
        strength = 0.0

    if len(other_nodes) > 0 and other_nodes[vol_col].sum() > 0:
        centroid = (other_nodes["Strike"] * other_nodes[vol_col]).sum() / other_nodes[vol_col].sum()
    else:
        centroid = primary_strike

    if strength < 0.80:
        state = "STRONG WALL"
        bias = "STABLE"
    elif centroid > primary_strike:
        state = f"WTT {strength * 100:.0f}%"
        bias = "BULLISH"
    elif centroid < primary_strike:
        state = f"WTB {strength * 100:.0f}%"
        bias = "BEARISH"
    else:
        state = "STRONG WALL"
        bias = "STABLE"

    return primary_strike, state, strength, bias


def smooth_bias(history: list, min_persistence: int = 2) -> str:
    """
    Hysteresis filter for a sequence of raw bias readings (STABLE/BULLISH/BEARISH),
    one per poll, oldest first. Only "confirms" a new bias once it has repeated
    for `min_persistence` consecutive polls in a row — walks the whole history
    tracking runs, so oscillation (bouncing between two states every poll)
    never confirms either one; it just holds whatever was last genuinely
    confirmed. A single blip doesn't flip the confirmed trend either.

    Pure function — caller (app.py) owns the actual history list in session
    state, since this module has no I/O of its own.
    """
    if not history:
        return "STABLE"

    confirmed = history[0]
    run_value = history[0]
    run_length = 1

    for val in history[1:]:
        if val == run_value:
            run_length += 1
        else:
            run_value = val
            run_length = 1
        if run_length >= min_persistence:
            confirmed = run_value

    return confirmed


# Explicit lookup for all 9 documented COA 1.0 scenarios, keyed by
# (support_bias, resistance_bias). This replaces an earlier if/elif chain
# whose catch-all "else" accidentally treated two genuinely tradeable
# scenarios (3 and 4 below) as a halt-worthy conflict — a real bug, not a
# style choice. Being exhaustive over all 9 combinations means there's no
# catch-all left to accidentally swallow a real scenario again.
#
# Bias values: STABLE = "Strong", BULLISH = "WTT", BEARISH = "WTB"
# (support_bias, resistance_bias) -> (scenario_number, name, risk_mode)
SCENARIO_MATRIX = {
    ("STABLE", "STABLE"):  (1, "Strong range consolidation", "NORMAL_LOTS"),
    ("STABLE", "BEARISH"): (2, "Slight bearish drop", "REDUCED_LOTS"),
    ("STABLE", "BULLISH"): (3, "Slight bullish rally", "REDUCED_LOTS"),
    ("BEARISH", "STABLE"): (4, "Extra bearish breakdown", "REDUCED_LOTS"),
    ("BULLISH", "STABLE"): (5, "Extra bullish breakout", "REDUCED_LOTS"),
    ("BEARISH", "BEARISH"): (6, "Severe bearish bloodbath", "SCALE_DOWN"),
    ("BULLISH", "BULLISH"): (7, "Powerful bull run", "SCALE_DOWN"),
    ("BULLISH", "BEARISH"): (8, "Gridlock / contraction — no-trade", "HALT_TRADING"),
    ("BEARISH", "BULLISH"): (9, "Diverging chaos — no-trade", "HALT_TRADING"),
}


def analyze_coa_matrix_structure(df: pd.DataFrame, spot: float, step: int) -> dict:
    """Processes one option-chain snapshot into COA structural coordinates."""
    base_strike = (spot // step) * step
    strike_above = base_strike + step

    call_scan = df[df["Strike"] >= base_strike].copy()
    resistance_strike, res_state, call_strength, res_bias = _side_analysis(
        df, "Call_Vol", call_scan
    )

    put_scan = df[df["Strike"] <= strike_above].copy()
    support_strike, sup_state, put_strength, sup_bias = _side_analysis(
        df, "Put_Vol", put_scan
    )

    atm_call_ltp = (
        df.loc[df["Strike"] == base_strike, "Call_LTP"].values[0]
        if base_strike in df["Strike"].values
        else 40.0
    )
    atm_put_ltp = (
        df.loc[df["Strike"] == strike_above, "Put_LTP"].values[0]
        if strike_above in df["Strike"].values
        else 40.0
    )
    avg_premium = (atm_call_ltp + atm_put_ltp) / 2

    eos = support_strike - avg_premium
    eor = resistance_strike + avg_premium

    # Alternate EOS/EOR method (per a separately supplied production spec):
    # uses ONLY the primary node's own LTP, rather than averaging with the
    # opposite side's ATM premium. Kept side-by-side with the method above
    # rather than replacing it — shown on the dashboard for comparison so a
    # trader can judge which tracks real reactions more closely over time.
    resistance_ltp_at_r1 = (
        df.loc[df["Strike"] == resistance_strike, "Call_LTP"].values[0]
        if resistance_strike in df["Strike"].values
        else atm_call_ltp
    )
    support_ltp_at_s1 = (
        df.loc[df["Strike"] == support_strike, "Put_LTP"].values[0]
        if support_strike in df["Strike"].values
        else atm_put_ltp
    )
    eos_alt = support_strike - support_ltp_at_s1
    eor_alt = resistance_strike + resistance_ltp_at_r1

    scenario_number, scenario, risk_mode = SCENARIO_MATRIX[(sup_bias, res_bias)]

    return {
        "base_zone": f"{int(base_strike)} - {int(strike_above)}",
        "base_strike": base_strike,
        "strike_above": strike_above,
        "support": support_strike,
        "support_state": sup_state,
        "support_ratio": put_strength,
        "support_bias": sup_bias,
        "resistance": resistance_strike,
        "resistance_state": res_state,
        "resistance_ratio": call_strength,
        "resistance_bias": res_bias,
        "eos": eos,
        "eor": eor,
        # Raw EOS/EOR inputs, exposed so the dashboard can show its work
        # instead of the formula being a black box:
        "atm_call_ltp": atm_call_ltp,
        "atm_put_ltp": atm_put_ltp,
        "avg_premium": avg_premium,
        # Alternate method (primary strike's own LTP only) for comparison:
        "eos_alt": eos_alt,
        "eor_alt": eor_alt,
        "resistance_ltp_at_r1": resistance_ltp_at_r1,
        "support_ltp_at_s1": support_ltp_at_s1,
        "scenario": scenario,
        "scenario_number": scenario_number,
        "risk_mode": risk_mode,
    }


def compute_range_target(eos: float, eor: float) -> float:
    """
    Middle-of-the-range profit target — per Playbook A (Scenario 1, Dot-to-Dot
    Reversal): "the immediate opposite diversion point (the middle of the range)".
    """
    return (eos + eor) / 2.0


def choose_t1_target(entry: float, fallback_target: float, candidates: list, direction: str) -> float:
    """
    Prefers an active migration-based diversion pivot (UR/US) as T1 if it
    sits meaningfully between entry and the fallback target in the trade's
    favorable direction — closer pivots are chosen first (a nearer,
    already-proven level is a safer first target than a further one).
    Falls back to fallback_target (typically the range midpoint) if no
    candidate qualifies.

    direction: "up" for a CALL trade (price expected to rise from entry),
               "down" for a PUT trade (price expected to fall from entry).
    """
    valid = []
    for c in candidates:
        if c is None:
            continue
        if direction == "up" and entry < c < fallback_target:
            valid.append(c)
        elif direction == "down" and fallback_target < c < entry:
            valid.append(c)
    if not valid:
        return fallback_target
    return min(valid, key=lambda c: abs(c - entry))


def select_otm_strike(entry_price: float, step: int, option_type: str) -> int:
    """
    Picks the strike to actually buy, derived from the EOS/EOR entry price
    itself — not a fixed offset from the DIL.

    Verified against a worked example rather than assumed: naive "nearest
    strike" rounding gives the WRONG strike here. The real rule is:
      - CE (call): ceiling — the next strike AT OR ABOVE the entry price
      - PE (put):  floor   — the next strike AT OR BELOW the entry price
    This keeps the bought option genuinely OTM relative to the reversal
    point, which is the actual intent ("nearest OTM strike"), even though
    it isn't the numerically nearest strike in the naive rounding sense.
    """
    if option_type == "CE":
        return int(math.ceil(entry_price / step) * step)
    return int(math.floor(entry_price / step) * step)


def compute_final_lots(base_lots: int, risk_mode: str) -> tuple[int, bool]:
    """Returns (final_lots, execution_permitted) given the risk mode."""
    if risk_mode == "HALT_TRADING":
        return 0, False
    if risk_mode == "SCALE_DOWN":
        return max(1, int(base_lots * 0.5)), True
    if risk_mode == "REDUCED_LOTS":
        return max(1, int(base_lots * 0.75)), True
    return base_lots, True
