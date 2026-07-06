"""
COA Dashboard — app.py
-----------------------
Run with:  streamlit run app.py

Screens:
  1. Live Signals   - COA summary cards, condensed strike ladder with
                       change-highlighting, active trade card (entry/SL/T1/T2,
                       live P&L, rationale, scenario win-rate), forming-trade note
  2. Trade History   - last-month closed trades table, summary stats,
                       equity curve, per-scenario win-rate breakdown
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

from engine.coa_math import analyze_coa_matrix_structure, compute_final_lots
from engine.data_feed import get_option_chain
from db.ledger import (
    init_db, open_trade, get_active_trade, close_trade,
    get_trade_history, get_monthly_summary, get_scenario_stats,
)

st.set_page_config(page_title="COA Dashboard", layout="wide")
init_db()

if "prev_chain" not in st.session_state:
    st.session_state.prev_chain = None

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
st.sidebar.title("COA controls")
selected_index = st.sidebar.selectbox("Index", ["NIFTY 50", "BANK NIFTY"])
base_lots = st.sidebar.slider("Base lot size", 1, 20, 4)
history_days = st.sidebar.slider("History window (days)", 7, 90, 30)
auto_refresh = st.sidebar.checkbox("Auto-refresh (10s)", value=False)

if selected_index == "NIFTY 50":
    index_ticker, index_spot, step_size = "NSE_INDEX|Nifty 50", 24440.85, 50
else:
    index_ticker, index_spot, step_size = "NSE_INDEX|Nifty Bank", 51820.40, 100

page = st.sidebar.radio("View", ["Live signals", "Trade history"])

# ---------------------------------------------------------------------------
# DATA PULL + COA CALCULATION
# ---------------------------------------------------------------------------
raw_chain_df = get_option_chain(index_ticker, index_spot, step_size)
metrics = analyze_coa_matrix_structure(raw_chain_df, index_spot, step_size)
final_lots, execution_permitted = compute_final_lots(base_lots, metrics["risk_mode"])


def build_rationale(m: dict) -> str:
    if m["risk_mode"] == "HALT_TRADING":
        return "Both walls are showing conflicting vectors — sitting out until one side clears."
    if "REDUCED" in m["risk_mode"] or "SCALE" in m["risk_mode"]:
        weak_side = "resistance" if "BEARISH" in m["resistance_bias"] else "support"
        return (f"{weak_side.title()} wall at {int(m[weak_side])} is showing a "
                f"{m[weak_side + '_state']} — pressure building in that direction.")
    return f"Support at {int(m['support'])} and resistance at {int(m['resistance'])} both holding as strong walls."


# ---------------------------------------------------------------------------
# LIVE SIGNALS PAGE
# ---------------------------------------------------------------------------
if page == "Live signals":
    st.title("COA live signals")

    c1, c2, c3 = st.columns(3)
    c1.metric("Support wall", f"{int(metrics['support'])}", metrics["support_state"])
    c2.metric("Resistance wall", f"{int(metrics['resistance'])}", metrics["resistance_state"])
    c3.metric("Risk mode", metrics["risk_mode"], f"{final_lots} lots" if execution_permitted else "halted")

    if metrics["risk_mode"] == "HALT_TRADING":
        st.error(f"Trading halted — {metrics['scenario']}")
    else:
        st.success(f"{metrics['scenario']}")
    st.caption(build_rationale(metrics))

    st.markdown("---")

    # --- Condensed strike ladder with change-highlighting ---
    st.subheader("Strike ladder (near-the-money)")
    zone_df = raw_chain_df[
        (raw_chain_df["Strike"] >= metrics["base_strike"] - 3 * step_size) &
        (raw_chain_df["Strike"] <= metrics["strike_above"] + 3 * step_size)
    ].copy()

    prev = st.session_state.prev_chain
    if prev is not None:
        merged = zone_df.merge(prev[["Strike", "Call_Vol", "Put_Vol"]],
                                on="Strike", suffixes=("", "_prev"), how="left")
        merged["Call_Vol_Delta"] = merged["Call_Vol"] - merged["Call_Vol_prev"].fillna(merged["Call_Vol"])
        merged["Put_Vol_Delta"] = merged["Put_Vol"] - merged["Put_Vol_prev"].fillna(merged["Put_Vol"])
    else:
        merged = zone_df.copy()
        merged["Call_Vol_Delta"] = 0
        merged["Put_Vol_Delta"] = 0

    def highlight_walls(row):
        styles = [""] * len(row)
        if row["Strike"] == metrics["resistance"]:
            styles = ["background-color: rgba(214,69,49,0.15)"] * len(row)
        elif row["Strike"] == metrics["support"]:
            styles = ["background-color: rgba(29,158,117,0.15)"] * len(row)
        return styles

    display_cols = ["Strike", "Call_Vol", "Call_Vol_Delta", "Call_OI",
                     "Put_OI", "Put_Vol_Delta", "Put_Vol"]
    st.dataframe(
        merged[display_cols].style.apply(highlight_walls, axis=1).format({
            "Call_Vol": "{:,.0f}", "Call_Vol_Delta": "{:+,.0f}", "Call_OI": "{:,.0f}",
            "Put_OI": "{:,.0f}", "Put_Vol_Delta": "{:+,.0f}", "Put_Vol": "{:,.0f}",
        }),
        use_container_width=True,
    )
    st.session_state.prev_chain = raw_chain_df.copy()

    st.markdown("---")

    # --- Active trade card ---
    st.subheader("Active / probable trade")
    active = get_active_trade()

    if active:
        current_price = index_spot
        direction = 1 if "CALL" in active["trade_type"] else -1
        point_delta = (current_price - active["entry_spot"]) * direction
        live_pnl = point_delta * active["lots"] * 50 * 0.55
        loss_if_sl = -abs(active["entry_spot"] - active["sl_spot"]) * active["lots"] * 50 * 0.55
        risk = abs(active["entry_spot"] - active["sl_spot"])
        reward = abs(active["t1_spot"] - active["entry_spot"])
        rr = round(reward / risk, 2) if risk else 0

        scen_stats = get_scenario_stats(active.get("scenario", ""), days=history_days)

        with st.container(border=True):
            st.markdown(f"**{active['trade_type']} — {active['strike_traded']}**  \n"
                        f"opened {active['timestamp_in']}")
            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Live P&L", f"₹{live_pnl:,.0f}")
            pc2.metric("If SL hits", f"₹{loss_if_sl:,.0f}")
            pc3.metric("Risk:Reward", f"1 : {rr}")
            pc4.metric("Lots", active["lots"])

            st.write(
                f"SL `{active['sl_spot']:.0f}` — Entry `{active['entry_spot']:.0f}` — "
                f"Spot `{current_price:.0f}` — T1 `{active['t1_spot']:.0f}` — T2 `{active['t2_spot']:.0f}`"
            )

            if scen_stats["total"] > 0:
                st.caption(f"This scenario has hit T1 in {scen_stats['wins']} of "
                           f"{scen_stats['total']} setups ({scen_stats['win_rate']}%) "
                           f"over the last {history_days} days.")
            else:
                st.caption("Not enough closed trades yet to show a scenario win-rate — "
                           "keep logging to build this up.")

            b1, b2, b3 = st.columns(3)
            if b1.button("Exit at T1"):
                pnl = (active["t1_spot"] - active["entry_spot"]) * direction * active["lots"] * 50 * 0.55
                close_trade(active["id"], active["t1_spot"], "Target 1 reached", pnl)
                st.rerun()
            if b2.button("Exit at T2"):
                pnl = (active["t2_spot"] - active["entry_spot"]) * direction * active["lots"] * 50 * 0.55
                close_trade(active["id"], active["t2_spot"], "Target 2 reached", pnl)
                st.rerun()
            if b3.button("Force square-off"):
                close_trade(active["id"], current_price, "Manual square-off", loss_if_sl)
                st.rerun()
    else:
        st.info("No open position. Standing by for spot to reach EOS/EOR.")
        cta1, cta2 = st.columns(2)
        with cta1:
            st.markdown(f"**Call setup (support side)**  \n"
                        f"Entry (EOS) `{metrics['eos']:.2f}` · SL `{metrics['eos'] - step_size * 0.4:.2f}` · "
                        f"T1 `{metrics['eos'] + step_size:.2f}` · T2 `{metrics['eor']:.2f}`")
            if execution_permitted and st.button("Open CALL position"):
                open_trade({
                    "timestamp_in": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ticker": selected_index, "trade_type": "CALL",
                    "strike_traded": f"{int(metrics['base_strike'] - step_size)} CE",
                    "scenario": metrics["scenario"], "lots": final_lots,
                    "entry_spot": index_spot, "sl_spot": metrics["eos"] - step_size * 0.4,
                    "t1_spot": metrics["eos"] + step_size, "t2_spot": metrics["eor"],
                })
                st.rerun()
        with cta2:
            st.markdown(f"**Put setup (resistance side)**  \n"
                        f"Entry (EOR) `{metrics['eor']:.2f}` · SL `{metrics['eor'] + step_size * 0.4:.2f}` · "
                        f"T1 `{metrics['eor'] - step_size:.2f}` · T2 `{metrics['eos']:.2f}`")
            if execution_permitted and st.button("Open PUT position"):
                open_trade({
                    "timestamp_in": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ticker": selected_index, "trade_type": "PUT",
                    "strike_traded": f"{int(metrics['strike_above'] + step_size)} PE",
                    "scenario": metrics["scenario"], "lots": final_lots,
                    "entry_spot": index_spot, "sl_spot": metrics["eor"] + step_size * 0.4,
                    "t1_spot": metrics["eor"] - step_size, "t2_spot": metrics["eos"],
                })
                st.rerun()

    if auto_refresh:
        st.rerun()

# ---------------------------------------------------------------------------
# TRADE HISTORY PAGE
# ---------------------------------------------------------------------------
else:
    st.title(f"Trade history — last {history_days} days")

    summary = get_monthly_summary(days=history_days)
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Total trades", summary["total_trades"])
    h2.metric("Net P&L", f"₹{summary['net_pnl']:,.0f}")
    h3.metric("Win rate", f"{summary['win_rate']}%")
    h4.metric("Wins / losses", f"{summary['wins']} / {summary['losses']}")

    hist_df = get_trade_history(days=history_days)

    if hist_df.empty:
        st.info("No closed trades yet in this window. Once trades are closed from "
                "the Live signals page, they'll show up here.")
    else:
        st.markdown("---")
        st.subheader("Equity curve")
        hist_df_sorted = hist_df.sort_values("timestamp_out")
        hist_df_sorted["cumulative_pnl"] = hist_df_sorted["net_pnl"].cumsum()
        fig = px.line(hist_df_sorted, x="timestamp_out", y="cumulative_pnl",
                      labels={"cumulative_pnl": "Cumulative P&L (₹)", "timestamp_out": "Closed at"})
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Win rate by scenario")
        if "scenario" in hist_df.columns:
            scenario_summary = (
                hist_df.groupby("scenario")
                .agg(trades=("net_pnl", "count"),
                     wins=("net_pnl", lambda s: (s > 0).sum()),
                     net_pnl=("net_pnl", "sum"))
                .reset_index()
            )
            scenario_summary["win_rate_%"] = (scenario_summary["wins"] / scenario_summary["trades"] * 100).round(1)
            st.dataframe(scenario_summary, use_container_width=True)

        st.markdown("---")
        st.subheader("All closed trades")
        show_cols = ["timestamp_in", "timestamp_out", "ticker", "trade_type",
                     "strike_traded", "scenario", "lots", "entry_spot", "exit_spot",
                     "sl_spot", "t1_spot", "t2_spot", "exit_reason", "net_pnl"]
        st.dataframe(hist_df[show_cols], use_container_width=True)
