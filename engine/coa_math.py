"""
COA Mathematical Core
----------------------
Implements the Chart of Accuracy structural analysis:
  - Support / Resistance wall detection (max Volume/OI strike)
  - WTT / WTB directional vectors (second-highest node comparison)
  - EOS / EOR entry level calculation
  - Scenario classification + risk sizing mode

This module is pure logic (no Streamlit, no I/O) so it can be unit tested
independently of the dashboard.
"""

import pandas as pd


def _side_analysis(df: pd.DataFrame, vol_col: str, scan_df: pd.DataFrame):
    """
    Shared logic for one side of the chain (calls or puts).
    Returns (primary_strike, state_label, strength_ratio, bias).
    """
    idx_primary = scan_df[vol_col].idxmax()
    primary_strike = scan_df.loc[idx_primary, "Strike"]

    sorted_df = scan_df.sort_values(by=vol_col, ascending=False).reset_index(drop=True)

    if len(sorted_df) > 1:
        secondary_strike = sorted_df.loc[1, "Strike"]
        secondary_vol = sorted_df.loc[1, vol_col]
        primary_vol = sorted_df.loc[0, vol_col]
        strength = (secondary_vol / primary_vol) if primary_vol > 0 else 0.0
    else:
        secondary_strike = primary_strike
        strength = 0.0

    if strength < 0.80:
        state = "STRONG WALL"
        bias = "STABLE"
    elif secondary_strike > primary_strike:
        state = f"WTT {strength * 100:.0f}%"
        bias = "BULLISH"
    elif secondary_strike < primary_strike:
        state = f"WTB {strength * 100:.0f}%"
        bias = "BEARISH"
    else:
        state = "STRONG WALL"
        bias = "STABLE"

    return primary_strike, state, strength, bias


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

    if res_bias == "STABLE" and sup_bias == "STABLE":
        scenario = "Strong range consolidation"
        risk_mode = "NORMAL_LOTS"
    elif res_bias == "BEARISH" and sup_bias == "STABLE":
        scenario = "Bearish breakdown building"
        risk_mode = "REDUCED_LOTS"
    elif sup_bias == "BULLISH" and res_bias == "STABLE":
        scenario = "Bullish rally accumulation"
        risk_mode = "REDUCED_LOTS"
    elif res_bias == "BEARISH" and sup_bias == "BEARISH":
        scenario = "Severe bearish pressure"
        risk_mode = "SCALE_DOWN"
    elif res_bias == "BULLISH" and sup_bias == "BULLISH":
        scenario = "Powerful bull run"
        risk_mode = "SCALE_DOWN"
    else:
        scenario = "Contradictory conflict"
        risk_mode = "HALT_TRADING"

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
        "scenario": scenario,
        "risk_mode": risk_mode,
    }


def compute_final_lots(base_lots: int, risk_mode: str) -> tuple[int, bool]:
    """Returns (final_lots, execution_permitted) given the risk mode."""
    if risk_mode == "HALT_TRADING":
        return 0, False
    if risk_mode == "SCALE_DOWN":
        return max(1, int(base_lots * 0.5)), True
    if risk_mode == "REDUCED_LOTS":
        return max(1, int(base_lots * 0.75)), True
    return base_lots, True
