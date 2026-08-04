"""Streamlit rendering for the read-only CQRP Decision Workstation."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Mapping

from dashboard.option_ladder import filter_ladder_around_atm
from dashboard.structure_trails import build_level_trail, build_wall_trails

from .components import metric_card, reason_list, status_badge


def render_top_bar(st: Any, dashboard: Mapping[str, Any]) -> None:
    snapshot = dashboard.get("snapshot") or {}
    operations = dashboard.get("operations") or {}
    status, source, version, quality, freshness = st.columns((1.1, 1.2, 1.2, 1.2, 1.5))
    status.markdown(status_badge("Mode", "PAPER ONLY"), unsafe_allow_html=True)
    source.markdown(metric_card("Data source", snapshot.get("market_source") or "FYERS", note="canonical snapshot"), unsafe_allow_html=True)
    version.markdown(metric_card("CQRP", "v2 research", note="no live execution"), unsafe_allow_html=True)
    quality.markdown(metric_card("Data quality", snapshot.get("data_quality_status") or "Awaiting"), unsafe_allow_html=True)
    freshness.markdown(metric_card("Last snapshot", _time(snapshot.get("market_captured_at")), note=f"Worker: {operations.get('worker') or 'LOCAL'}"), unsafe_allow_html=True)


def render_sidebar_context(st: Any, dashboard: Mapping[str, Any]) -> None:
    operations = dashboard.get("operations") or {}
    evidence = dashboard.get("scenario_evidence") or {}
    st.sidebar.markdown("### System monitor")
    st.sidebar.caption(f"Worker: {operations.get('worker') or 'Awaiting'}")
    st.sidebar.caption(f"Data quality: {operations.get('data_quality') or 'Awaiting'}")
    st.sidebar.caption(f"Open paper trades: {operations.get('open_paper_trades') or 0}")
    st.sidebar.markdown(status_badge(evidence.get("label") or "Scenario evidence", evidence.get("status") or "UPCOMING"), unsafe_allow_html=True)
    st.sidebar.caption(evidence.get("detail") or "")
    st.sidebar.markdown("### Intraday story trail")
    events = list(dashboard.get("events") or [])[-8:]
    if not events:
        st.sidebar.caption("Awaiting persisted structure events.")
        return
    for event in reversed(events):
        st.sidebar.caption(f"{_time(event.get('occurred_at'))} · {str(event.get('event_type') or '').replace('_', ' ').title()}")


def render_live_cockpit(st: Any, dashboard: Mapping[str, Any]) -> None:
    decision = dashboard["decision"]
    cards = decision.cards
    st.subheader("Live Cockpit")
    render_top_bar(st, dashboard)
    if decision.error:
        st.info(decision.error)
        return
    left, centre, right = st.columns((1.25, 1.45, 1.4))
    with left:
        _render_decision(st, cards)
    with centre:
        _render_index_comparison(st, dashboard.get("comparison") or [])
    with right:
        _render_market_snapshot(st, cards, dashboard.get("snapshot") or {})
    map_column, option_column, plan_column = st.columns((1.55, 1.1, 0.8))
    with map_column:
        render_structure_map(st, dashboard)
    with option_column:
        render_options_intelligence(st, dashboard, compact=True)
    with plan_column:
        render_conditional_plan(st, dashboard.get("plan") or {}, dashboard.get("premarket_validation"))
    plan_column, portfolio_column, research_column = st.columns((1.1, 1.0, 1.0))
    with plan_column:
        render_tomorrow_plans(st, dashboard.get("plan") or {})
    with portfolio_column:
        _render_paper_portfolio(st, cards)
    with research_column:
        _render_research_status(st, dashboard.get("scenario_evidence") or {})


def render_structure_map(st: Any, dashboard: Mapping[str, Any]) -> None:
    st.markdown("#### CQRP Structure Map")
    points, markers = build_level_trail(dashboard.get("events") or [])
    if not points:
        st.info("Structure map will appear after persisted intraday structure snapshots are available.")
        return
    import plotly.graph_objects as go

    colors = {"spot": "#e5edf5", "support": "#22c55e", "eos": "#facc15", "resistance": "#ef4444", "eor": "#60a5fa"}
    figure = go.Figure()
    for field, label in (("spot", "Spot"), ("support", "Support"), ("eos", "EOS"), ("resistance", "Resistance"), ("eor", "EOR")):
        values = [point.get(field) for point in points]
        if any(value is not None for value in values):
            figure.add_trace(go.Scatter(x=[point["timestamp"] for point in points], y=values, mode="lines", name=label, connectgaps=True, line={"color": colors[field], "width": 2.7 if field == "spot" else 1.4, "dash": "solid" if field == "spot" else "dot"}))
    if markers:
        figure.add_trace(go.Scatter(x=[item["timestamp"] for item in markers], y=[item["spot"] for item in markers], mode="markers", name="Recorded event", marker={"color": "#f59e0b", "symbol": "diamond", "size": 8}, text=[item["detail"] for item in markers], hovertemplate="%{text}<br>%{x}<br>Spot: %{y:.2f}<extra></extra>"))
    figure.update_layout(height=410, margin={"l": 18, "r": 12, "t": 26, "b": 34}, hovermode="x unified", legend={"orientation": "h", "y": -0.22}, xaxis_title="Market time", yaxis_title="Index level")
    st.plotly_chart(figure, width="stretch")
    st.caption("Dynamic levels are research evidence, not a trade instruction. The latest snapshot determines current levels.")


def render_options_intelligence(st: Any, dashboard: Mapping[str, Any], *, compact: bool = False) -> None:
    st.markdown("#### Options Intelligence")
    ladder = filter_ladder_around_atm(dashboard.get("ladder") or [], 5 if compact else 10)
    if not ladder:
        st.info("Awaiting a captured option chain.")
        return
    rows = [{"CE OI Δ": item.get("ce_oi_change"), "CE Vol": item.get("ce_volume"), "Strike": item.get("strike"), "PE Vol": item.get("pe_volume"), "PE OI Δ": item.get("pe_oi_change")} for item in ladder]
    st.dataframe(rows, width="stretch", hide_index=True, height=210 if compact else None)
    render_option_activity(st, dashboard.get("activity") or [], dashboard.get("walls") or [])


def render_option_activity(st: Any, activity: list[Mapping[str, Any]], walls: list[Mapping[str, Any]] | None = None) -> None:
    st.markdown("##### Option-Chain Activity")
    if not activity:
        return
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    strikes = [item["strike"] for item in activity]
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(go.Bar(name="CE OI", x=strikes, y=[-item["ce_oi"] for item in activity], marker_color="#b45353"), secondary_y=False)
    figure.add_trace(go.Bar(name="PE OI", x=strikes, y=[item["pe_oi"] for item in activity], marker_color="#3c8a60"), secondary_y=False)
    figure.add_trace(go.Scatter(name="Volume", x=strikes, y=[item["ce_volume"] + item["pe_volume"] for item in activity], line={"color": "#eab308", "width": 1.7}), secondary_y=True)
    figure.add_trace(go.Scatter(name="OI change", x=strikes, y=[item["pe_oi_change"] - item["ce_oi_change"] for item in activity], line={"color": "#60a5fa", "width": 1.7}), secondary_y=True)
    for index, item in enumerate(activity):
        if item.get("is_atm"):
            figure.add_vline(x=strikes[index], line_color="#60a5fa", line_width=2, annotation_text="ATM", annotation_position="top")
    migration = _latest_wall_migration(walls or [])
    if migration:
        figure.add_annotation(x=strikes[-1], y=max([item["pe_oi"] for item in activity] or [0]), text=migration, showarrow=False, xanchor="right", yanchor="bottom", font={"size": 10, "color": "#cbd5e1"})
    figure.update_layout(barmode="relative", height=255, margin={"l": 12, "r": 12, "t": 26, "b": 34}, legend={"orientation": "h", "y": -0.32}, xaxis_title="Strike")
    figure.update_yaxes(title_text="OI (CE ← / PE →)", secondary_y=False)
    figure.update_yaxes(title_text="Activity", secondary_y=True)
    st.plotly_chart(figure, width="stretch")
    st.caption("Bars show current OI; lines show combined volume and net put-versus-call OI change. Recorded wall migration is annotated only when the persisted wall trail supports it.")


def render_conditional_plan(st: Any, plan: Mapping[str, Any], premarket: Mapping[str, Any] | None) -> None:
    st.markdown("#### Conditional Strike Plan")
    st.caption(plan.get("headline") or "No plan")
    if plan.get("state") == "NO_PLAN":
        st.info(plan.get("activation"))
        return
    st.write(f"Direction: {plan.get('direction') or '—'} {plan.get('option_type') or ''}")
    st.write(f"Expiry: {plan.get('expiry') or '—'}")
    st.write(f"Entry / stop: {plan.get('entry') or '—'} / {plan.get('stop_loss') or '—'}")
    st.write(f"Targets: {plan.get('target_1') or '—'} / {plan.get('target_2') or '—'}")
    st.caption(plan.get("activation"))
    if premarket:
        st.caption(f"Open validation: {premarket.get('validation_result') or 'RECORDED'}")
    st.warning(plan.get("invalidation"))


def render_tomorrow_plans(st: Any, plan: Mapping[str, Any]) -> None:
    st.markdown("#### Tomorrow Plan")
    opening = list(plan.get("opening_plans") or [])
    if not opening:
        st.caption("Gap Up / Gap Down / Flat cards appear after a qualifying pre-close plan is persisted.")
        return
    for item in opening:
        st.markdown(f"**Plan {item.get('code') or '—'}** · {item.get('opening_condition') or 'Conditional'}")
        st.caption(item.get("action") or "WAIT")
        st.caption(item.get("entry_condition") or "Await next-open confirmation")


def _render_decision(st: Any, cards: Mapping[str, Any]) -> None:
    st.markdown("#### CQRP Decision")
    st.markdown(metric_card("Action", cards.get("action"), note="research / PAPER only"), unsafe_allow_html=True)
    st.markdown(metric_card("Validation", cards.get("validation_score"), note=str(cards.get("confidence") or "Awaiting")), unsafe_allow_html=True)
    st.markdown("**Why CQRP gave this status**")
    for reason in reason_list(cards.get("rationale") or [])[:5]:
        st.caption(f"✓ {reason}")
    for warning in reason_list(cards.get("warnings") or [])[:3]:
        st.caption(f"! {warning}")


def _render_index_comparison(st: Any, rows: list[Mapping[str, Any]]) -> None:
    st.markdown("#### Index Opportunity Comparison")
    if not rows:
        st.caption("Rank only when each index has a fresh, persisted snapshot.")
        return
    for row in rows:
        st.markdown(metric_card(row.get("instrument") or "Index", row.get("score"), note=f"Rank {row.get('rank') or '—'} · {row.get('signal') or 'NO DATA'}"), unsafe_allow_html=True)


def _render_market_snapshot(st: Any, cards: Mapping[str, Any], snapshot: Mapping[str, Any]) -> None:
    st.markdown("#### Market Snapshot")
    for label, value in (("Spot", cards.get("spot")), ("Support", cards.get("support")), ("Resistance", cards.get("resistance")), ("EOS", cards.get("eos")), ("EOR", cards.get("eor"))):
        st.markdown(metric_card(label, value), unsafe_allow_html=True)
    st.caption(f"Execution quality is determined from quote coverage and liquidity validation. Source: {snapshot.get('market_source') or 'FYERS'}.")


def _render_paper_portfolio(st: Any, cards: Mapping[str, Any]) -> None:
    st.markdown("#### Paper Portfolio")
    trade = cards.get("trade")
    if not trade:
        st.caption("No active paper trade. CQRP is monitoring or declining candidates.")
        return
    st.write(f"{trade.get('instrument')} · {trade.get('direction')} · {trade.get('status')}")
    st.caption(f"Entry: {trade.get('entry') or trade.get('intended_entry') or '—'} · P&L: {trade.get('unrealized_pnl') or trade.get('realized_pnl') or '—'}")


def _render_research_status(st: Any, evidence: Mapping[str, Any]) -> None:
    st.markdown("#### Research Status")
    st.markdown(status_badge(evidence.get("label") or "Evidence", evidence.get("status") or "UPCOMING"), unsafe_allow_html=True)
    st.caption(evidence.get("detail") or "")
    if evidence.get("structural") is not None:
        st.caption(f"Current structural/tactical track: {evidence.get('structural')} / {evidence.get('tactical') or 'unclassified'}")


def _time(value: object) -> str:
    if not value:
        return "Awaiting"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%H:%M IST")
    except ValueError:
        return text


def _latest_wall_migration(walls: list[Mapping[str, Any]]) -> str | None:
    """Summarize a latest persisted top-wall movement without inferring a trade signal."""
    trails = build_wall_trails(walls)
    moved: list[str] = []
    for trail in trails:
        if int(trail.get("rank") or 0) != 1:
            continue
        points = trail.get("points") or []
        if len(points) < 2:
            continue
        previous, latest = points[-2], points[-1]
        if previous.get("strike") != latest.get("strike"):
            moved.append(f"{trail.get('side')} {trail.get('metric')}: {previous.get('strike'):.0f} → {latest.get('strike'):.0f}")
    return " | ".join(moved[:2]) if moved else None
