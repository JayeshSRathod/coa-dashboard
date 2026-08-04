"""Local Streamlit entrypoint for CQRP Dashboard 2.0."""

from pathlib import Path
import sys

# Streamlit executes this file as a script, making ``dashboard/`` the initial
# import root. Add the repository root so package imports work locally and in
# Streamlit Cloud deployments.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.services import DashboardApplicationService
from dashboard.exports import export_csv, export_json
from dashboard.configuration_page import render_configuration_page
from dashboard.observation_page import render_observation_page
from dashboard.structure_trails import build_level_trail, build_wall_trails
from dashboard.option_ladder import filter_ladder_around_atm
from dashboard.workstation import apply_workstation_theme, workstation_enabled
from dashboard.workstation.render import (
    render_conditional_plan,
    render_live_cockpit,
    render_options_intelligence,
    render_sidebar_context,
    render_structure_map,
)
from src.application.ai_service import CopilotApplicationService
from src.configuration_console import ConfigurationConsoleService
from src.market_data.contracts import OptionChainRequest
PAGES={"CQRPDW":"get_cqrpdw_dashboard","Market Intelligence":"get_market_dashboard","Scanner":"get_scanner_dashboard","COA Research":"get_coa_dashboard","Strike Activity":"get_dynamic_walls_dashboard","Strategy Lab":"get_strategy_lab_dashboard","Research Knowledge":"get_research_knowledge_dashboard","Local Research Assistant":"get_research_knowledge_dashboard","Portfolio":"get_portfolio_dashboard","Options Analytics":"get_options_dashboard","Trade Journal":"get_trade_journal_dashboard","Performance":"get_performance_dashboard","Execution":"get_execution_dashboard","Operations Center":"get_operations_dashboard","Alerts":"get_alert_dashboard","Observation Notes":"get_observation_notes_dashboard","Configuration":"get_configuration_dashboard"}
INSTRUMENT_SCOPED_PAGES={"CQRPDW","Market Intelligence","Scanner","COA Research","Strike Activity","Portfolio","Options Analytics","Trade Journal","Performance","Execution","Operations Center","Alerts"}
def main(service=None):
    import streamlit as st

    st.set_page_config(page_title="CQRP Dashboard 2.0", layout="wide")
    if workstation_enabled():
        _workstation_main(st, service)
        return
    page = st.sidebar.selectbox("CQRP Navigation", list(PAGES))
    instrument = st.sidebar.selectbox("Research instrument", ["NIFTY", "BANKNIFTY", "FINNIFTY"], help="Shared scope for all market-facing pages.")
    if page == "Configuration":
        render_configuration_page()
        return

    def render_page(active_service):
        if page == "Observation Notes":
            render_observation_page(active_service.manual_observations)
            return
        if page == "Local Research Assistant":
            _render_local_research_assistant(st, active_service.fyers_research, instrument)
            return
        if page == "Market Intelligence":
            _render_live_fyers_market(st, active_service, instrument)
            return
        if page == "COA Research":
            _render_coa_research(st, active_service, instrument)
            return
        if page == "Strike Activity":
            _render_strike_activity(st, active_service, instrument)
            return
        if page == "Options Analytics":
            _render_options_analytics(st, active_service, instrument)
            return
        if page in INSTRUMENT_SCOPED_PAGES:
            view = getattr(active_service, PAGES[page])(instrument=instrument)
        else:
            view = getattr(active_service, PAGES[page])()
        if page == "CQRPDW":
            _render_cqrpdw(st, view)
        else:
            _render_view(st, view)

    def render_with_service():
        # Streamlit fragments can execute in a different context from the
        # initial script run. Do not share a SQLite-backed service instance
        # across those contexts.
        active_service = service or DashboardApplicationService()
        owns_service = service is None
        try:
            render_page(active_service)
        finally:
            if owns_service:
                active_service.close()

    if hasattr(st, "fragment"):
        @st.fragment(run_every=60)
        def auto_refresh_page():
            render_with_service()
        auto_refresh_page()
    else:
        render_with_service()

def _render_view(st,view):
 st.title(view.title);st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 if view.error:st.warning(view.error)
 if view.cards:st.json(view.cards)
 if view.rows:
  st.dataframe(view.rows,width="stretch")
  _render_exports(st, view.rows, view.title)
 else:st.info("No data is currently available for this view.")

def _render_exports(st, rows, name):
 safe_name="".join(character.lower() if character.isalnum() else "_" for character in name).strip("_")
 left,right=st.columns(2)
 left.download_button("Download CSV", export_csv(rows), file_name=f"{safe_name}.csv", mime="text/csv", key=f"{safe_name}_csv")
 right.download_button("Download JSON", export_json(rows), file_name=f"{safe_name}.json", mime="application/json", key=f"{safe_name}_json")

def _render_decision_dashboard(st,view):
 st.title("Decision Dashboard");st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 cards=view.cards;action=str(cards.get("action","WAITING_FOR_DATA"));reason=str(cards.get("reason",""))
 if action=="NO_TRADE":st.warning(f"Action: {action} — {reason}")
 elif action.startswith("PAPER_"):st.success(f"Action: {action} — {reason}")
 else:st.info(f"Action: {action} — {reason}")
 first,second,third,fourth=st.columns(4)
 first.metric(f"{cards.get('instrument') or 'Market'} spot",cards.get("spot") or "—")
 second.metric("Validation",cards.get("validation_score") or "—")
 third.metric("Confidence",cards.get("confidence") or "—")
 fourth.metric("Signal",cards.get("signal_type") or "—")
 values=[("Support",cards.get("support")),("EOS",cards.get("eos")),("Spot",cards.get("spot")),("Resistance",cards.get("resistance")),("EOR",cards.get("eor"))]
 plotted=[(label,value) for label,value in values if value is not None]
 if plotted:
  import plotly.graph_objects as go
  figure=go.Figure(go.Scatter(x=[item[1] for item in plotted],y=[item[0] for item in plotted],mode="markers+text",text=[item[0] for item in plotted],textposition="top center",marker={"size":14,"color":["#3b82f6","#22c55e","#f59e0b","#ef4444","#a855f7"][:len(plotted)]}))
  figure.update_layout(title="COA market map",xaxis_title=f"{cards.get('instrument') or 'Market'} level",yaxis_title="",height=300,margin={"l":20,"r":20,"t":50,"b":30})
  st.plotly_chart(figure,width="stretch")
 st.subheader("Decision checks");st.dataframe(view.rows,width="stretch",hide_index=True)
 st.caption("This dashboard is research and PAPER-only. It does not submit a broker order.")

def _render_cqrpdw(st,view):
 st.title("CQRPDW — CQRP Decision Workstation");st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 cards=view.cards;action=str(cards.get("action","WAITING_FOR_DATA"));reason=str(cards.get("reason",""))
 if action=="NO_TRADE":st.warning(f"Action: {action} — {reason}")
 elif action.startswith("PAPER_"):st.success(f"Action: {action} — {reason}")
 else:st.info(f"Action: {action} — {reason}")
 first,second,third,fourth=st.columns(4)
 first.metric(f"{cards.get('instrument') or 'Market'} spot",cards.get("spot") or "—")
 second.metric("Validation",cards.get("validation_score") or "—")
 third.metric("Confidence",cards.get("confidence") or "—")
 fourth.metric("Paper phase",cards.get("phase") or "—")
 values=[("Support",cards.get("support")),("EOS",cards.get("eos")),("Spot",cards.get("spot")),("Resistance",cards.get("resistance")),("EOR",cards.get("eor"))]
 plotted=[(label,value) for label,value in values if value is not None]
 if plotted:
  import plotly.graph_objects as go
  figure=go.Figure(go.Scatter(x=[item[1] for item in plotted],y=[item[0] for item in plotted],mode="markers+text",text=[item[0] for item in plotted],textposition="top center",marker={"size":14,"color":["#3b82f6","#22c55e","#f59e0b","#ef4444","#a855f7"][:len(plotted)]}))
  figure.update_layout(title="COA market map",xaxis_title=f"{cards.get('instrument') or 'Market'} level",yaxis_title="",height=300,margin={"l":20,"r":20,"t":50,"b":30})
  st.plotly_chart(figure,width="stretch")
 st.subheader("Why CQRP gave this signal")
 rationale=cards.get("rationale") or []
 if rationale:
  for item in rationale:st.write(f"• {item}")
 else:st.info("No directional rationale is available for the latest snapshot.")
 warnings=cards.get("warnings") or []
 if warnings:st.warning("Warnings: " + " | ".join(str(item) for item in warnings))
 trade=cards.get("trade")
 st.subheader("Paper trade plan and live state")
 if trade:
  plan={"Direction":trade.get("direction"),"Contract":f"{trade.get('instrument')} {trade.get('strike') or ''} {trade.get('option_type') or ''}".strip(),"Quantity":trade.get("quantity"),"Entry":trade.get("entry") or trade.get("intended_entry"),"Stop":trade.get("stop_loss"),"T1":trade.get("target_1"),"T2":trade.get("target_2"),"Remaining":trade.get("quantity_remaining"),"Realised P&L":trade.get("realized_pnl"),"Unrealised P&L":trade.get("unrealized_pnl")}
  st.dataframe([plan],width="stretch",hide_index=True)
  lifecycle=cards.get("lifecycle") or []
  if lifecycle:
   st.subheader("Paper trade lifecycle")
   st.dataframe(lifecycle,width="stretch",hide_index=True)
  else:st.info("Signal is retained; its paper-trade lifecycle has not started yet.")
 else:st.info("No active paper trade. CQRP is currently monitoring or declining a trade.")
 st.subheader("Decision checks");st.dataframe(view.rows,width="stretch",hide_index=True)
 st.subheader("CQRP operational modules")
 modules=cards.get("modules") or {}
 if modules:
  feed_tab,market_tab,scanner_tab,risk_tab,analytics_tab,operations_tab=st.tabs(["Decision feed", "Market state", "Scanner", "Portfolio risk", "Journal & performance", "Operations"])
  with feed_tab:
   feed=modules.get("decision_feed") or []
   if feed:st.dataframe(feed,width="stretch",hide_index=True)
   else:st.info("The configured worker has not captured an instrument yet.")
  with market_tab:
   st.json({"market_state":modules.get("market_state"),"technical_confirmation":modules.get("technical_confirmation"),"options_analytics":modules.get("options_analytics")})
  with scanner_tab:
   candidates=modules.get("scanner") or []
   if candidates:st.dataframe(candidates,width="stretch",hide_index=True)
   else:st.info("No scanner candidate is available from the current data.")
  with risk_tab:
   if modules.get("risk"):st.json(modules["risk"])
   else:st.info("Portfolio-risk preview is waiting for a research signal.")
  with analytics_tab:
   st.json(modules.get("performance") or {})
   journal=modules.get("trade_journal") or []
   if journal:st.dataframe(journal,width="stretch",hide_index=True)
   else:st.info("Performance metrics will populate after paper trades are closed.")
  with operations_tab:st.json(modules.get("operations") or {})
 st.caption("CQRPDW is research and PAPER-only. It does not submit a broker order.")

def _render_coa_research(st, service, instrument):
 sessions=service.available_sessions(instrument)
 session=st.selectbox("Session", ["All sessions", *sessions], key="coa_session")
 selected_session=None if session=="All sessions" else session
 _render_intraday_structure_trail(st, service, instrument, selected_session or (sessions[0] if sessions else None))
 event_types=service.available_dynamic_event_types(instrument, selected_session)
 selected_events=st.multiselect("Structure events", event_types, default=event_types, key="coa_event_types")
 view=service.get_coa_dashboard(instrument=instrument, session_id=selected_session, event_types=tuple(selected_events))
 _render_view(st, view)
 st.caption("Events include COA1/COA2 scenario track, moving levels, breakout/retest evidence, and linked validation/risk/paper outcome IDs. Use Strike Activity for CE/PE strike-wall history.")

def _render_intraday_structure_trail(st, service, instrument, session_id):
 """Render full-session visual evidence without changing the research engine."""
 st.subheader("Intraday COA Structure Trail")
 if not session_id:
  st.info("The trail will appear after the first captured structure session.")
  return
 try:
  events=service.fyers_research.dynamic_events(instrument,session_id=session_id,event_types=(),limit=25_000)
  walls=service.fyers_research.dynamic_walls(instrument,session_id=session_id,limit=25_000)
 except Exception as exc:
  st.warning(f"Structure trail is unavailable: {exc}")
  return
 points,markers=build_level_trail(events)
 if not points:
  st.info(f"No structure snapshots are available for {session_id} yet.")
  return
 import plotly.graph_objects as go
 colors={"spot":"#f8fafc","support":"#22c55e","eos":"#38bdf8","resistance":"#ef4444","eor":"#a855f7"}
 figure=go.Figure()
 for field,label in (("spot","Spot"),("support","Support"),("eos","EOS"),("resistance","Resistance"),("eor","EOR")):
  values=[point.get(field) for point in points]
  if not any(value is not None for value in values):
   continue
  figure.add_trace(go.Scatter(x=[point["timestamp"] for point in points],y=values,mode="lines",name=f"{label} trail",connectgaps=True,line={"color":colors[field],"width":3 if field=="spot" else 1.5,"dash":"solid" if field=="spot" else "dot"},opacity=0.95 if field=="spot" else 0.48,hovertemplate=f"{label}: %{{y:.2f}}<br>%{{x}}<extra></extra>"))
  last=next((point for point in reversed(points) if point.get(field) is not None),None)
  if last and field!="spot":
   figure.add_trace(go.Scatter(x=[last["timestamp"]],y=[last[field]],mode="markers+text",name=f"Current {label}",text=[f"{label} now"],textposition="top center",marker={"color":colors[field],"size":9},showlegend=False,hovertemplate=f"Current {label}: %{{y:.2f}}<extra></extra>"))
 if st.checkbox("Show breakout, rejection and retest markers",value=True,key="structure_markers") and markers:
  figure.add_trace(go.Scatter(x=[item["timestamp"] for item in markers],y=[item["spot"] for item in markers],mode="markers",name="Structure event",marker={"color":"#facc15","symbol":"diamond","size":9},text=[f"{item['event_type']}: {item['detail']}" for item in markers],hovertemplate="%{text}<br>%{x}<br>Spot: %{y:.2f}<extra></extra>"))
 figure.update_layout(title=f"{instrument} — {session_id}",height=460,hovermode="x unified",legend={"orientation":"h","y":-0.22},margin={"l":20,"r":20,"t":50,"b":80},xaxis_title="Market time",yaxis_title="Index level")
 st.plotly_chart(figure,width="stretch")
 st.caption("Dim dotted lines show historical dynamic levels; labelled markers show the latest level. Yellow diamonds are recorded structural events, not trade instructions.")
 if st.checkbox("Show CE/PE top-wall strike trails",value=True,key="wall_trails"):
  wall_figure=go.Figure()
  line_colors={"CE":"#ef4444","PE":"#22c55e"}
  for trail in build_wall_trails(walls):
   rank=int(trail["rank"])
   points_for_wall=trail["points"]
   wall_figure.add_trace(go.Scatter(x=[point["timestamp"] for point in points_for_wall],y=[point["strike"] for point in points_for_wall],mode="lines",name=trail["label"],line={"color":line_colors.get(trail["side"],"#94a3b8"),"width":3 if rank==1 else 1,"dash":"solid" if trail["metric"]=="VOLUME" else "dash"},opacity={1:0.9,2:0.55,3:0.3}.get(rank,0.25),text=[f"{point.get('contract') or trail['label']}<br>Value: {point.get('metric_value')}" for point in points_for_wall],hovertemplate="%{text}<br>%{x}<br>Strike: %{y}<extra></extra>"))
  wall_figure.update_layout(title="Top CE/PE Volume and OI Wall-Strike Trail",height=360,hovermode="x unified",legend={"orientation":"h","y":-0.28},margin={"l":20,"r":20,"t":50,"b":90},xaxis_title="Market time",yaxis_title="Option strike")
  st.plotly_chart(wall_figure,width="stretch")
  st.caption("CE is red and PE is green; solid lines are volume walls, dashed lines are OI walls. Rank 1 is strongest; ranks 2–3 are dimmer context.")

def _render_strike_activity(st, service, instrument):
 sessions=service.available_sessions(instrument)
 session=st.selectbox("Session", ["All sessions", *sessions], key="walls_session")
 view=service.get_dynamic_walls_dashboard(instrument=instrument, session_id=None if session=="All sessions" else session)
 _render_view(st, view)
 st.caption("Each row is a top-three CE/PE Volume or OI wall at a specific strike. This is the auditable strike-level evidence behind support/resistance migration.")

def _render_options_analytics(st, service, instrument):
 view=service.get_options_dashboard(instrument=instrument)
 st.title("Options Analytics — Research Ladder")
 st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 if view.error:
  st.warning(view.error)
  return
 cards=view.cards
 first,second,third,fourth,fifth=st.columns(5)
 first.metric(f"{instrument} spot",cards.get("spot") or "—")
 second.metric("ATM",cards.get("atm") or "—")
 third.metric("PCR",_format_value(cards.get("pcr"),2))
 fourth.metric("Quote coverage",_format_percent(cards.get("quote_coverage")))
 fifth.metric("Average spread",_format_value(cards.get("average_spread"),2))
 st.caption(f"Expiry: {cards.get('expiry')} | Snapshot: {cards.get('captured_at')} | Bid/ask and Greeks are shown only when supplied by the provider.")
 if not view.rows:
  st.info("No option-chain contracts are available yet.")
  return
 strikes=st.slider("Strikes on each side of ATM",min_value=1,max_value=max(1,(len(view.rows)-1)//2),value=min(10,max(1,(len(view.rows)-1)//2)),key="option_ladder_strikes")
 ladder=filter_ladder_around_atm(view.rows,strikes)
 show_greeks=st.checkbox("Show Greeks context",value=False,key="option_ladder_greeks")
 table=[]
 for row in ladder:
  item={
   "CE OI Δ":row.get("ce_oi_change"),"CE Volume":row.get("ce_volume"),"CE Bid":row.get("ce_bid"),"CE Ask":row.get("ce_ask"),"CE LTP":row.get("ce_ltp"),"CE Spread":row.get("ce_spread"),
   "STRIKE":f"{row['strike']:.0f}" + ("  ← ATM" if row.get("is_atm") else ""),
   "PE LTP":row.get("pe_ltp"),"PE Bid":row.get("pe_bid"),"PE Ask":row.get("pe_ask"),"PE Spread":row.get("pe_spread"),"PE Volume":row.get("pe_volume"),"PE OI Δ":row.get("pe_oi_change"),
  }
  if show_greeks:
   item.update({"CE Δ":row.get("ce_delta"),"CE Γ":row.get("ce_gamma"),"CE Θ":row.get("ce_theta"),"CE Vega":row.get("ce_vega"),"CE IV":row.get("ce_iv"),"PE IV":row.get("pe_iv"),"PE Vega":row.get("pe_vega"),"PE Θ":row.get("pe_theta"),"PE Γ":row.get("pe_gamma"),"PE Δ":row.get("pe_delta")})
  table.append(item)
 st.subheader("Calls ← | Strike | → Puts")
 st.dataframe(table,width="stretch",hide_index=True)
 st.caption("The ladder is an evidence view, not a trade instruction. ATM is the strike nearest current spot. Blank quote/Greek cells mean the market-data provider did not supply that field.")
 metric=st.radio("Compare option-chain activity",["Open interest","Volume","OI change"],horizontal=True,key="option_ladder_metric")
 field={"Open interest":"oi","Volume":"volume","OI change":"oi_change"}[metric]
 import plotly.graph_objects as go
 figure=go.Figure()
 figure.add_trace(go.Bar(name="CE",y=[str(int(row["strike"])) for row in ladder],x=[-(row.get(f"ce_{field}") or 0) for row in ladder],orientation="h",marker_color="#ef4444",hovertemplate="CE %{y}: %{x}<extra></extra>"))
 figure.add_trace(go.Bar(name="PE",y=[str(int(row["strike"])) for row in ladder],x=[row.get(f"pe_{field}") or 0 for row in ladder],orientation="h",marker_color="#22c55e",hovertemplate="PE %{y}: %{x}<extra></extra>"))
 figure.update_layout(title=f"{metric}: CE left / PE right",barmode="relative",height=420,margin={"l":25,"r":25,"t":50,"b":30},xaxis_title=metric,yaxis_title="Strike")
 st.plotly_chart(figure,width="stretch")
 _render_exports(st,table,f"{instrument}_option_ladder")

def _format_value(value, decimals):
 return "—" if value is None else f"{float(value):.{decimals}f}"

def _format_percent(value):
 return "—" if value is None else f"{float(value)*100:.0f}%"

def _render_local_research_assistant(st, research, instrument):
 st.title("Local Research Assistant")
 st.caption("Optional local Ollama analysis. Advisory only: it cannot create orders, change COA, alter risk, or train itself from CQRP data.")
 assistant=CopilotApplicationService()
 try:
  enabled=bool(ConfigurationConsoleService().public_configuration()["local_ai"]["ollama_enabled"])
 except Exception as exc:
  st.error(f"Local AI configuration is unavailable: {exc}")
  return
 if not enabled:
  st.info("Local advisory is OFF. Enable it in Configuration → Local AI when you want a local, evidence-based report. CQRP will not contact Ollama while it is OFF.")
  return
 status=assistant.local_ollama_status(enabled=True)
 if not status.get("reachable"):
  st.warning("Local Ollama is not reachable. The existing Offline Evidence Copilot remains available.")
  if status.get("reason"): st.caption(status["reason"])
  return
 st.success("Ollama is reachable on the local machine. No CQRP data leaves this computer.")
 sessions=research.dynamic_sessions(instrument)
 if not sessions:
  st.info("No captured dynamic-structure sessions are available for this instrument yet.")
  return
 session=st.selectbox("CQRP session", sessions, key="local_research_session")
 expiry=st.text_input("Expiry filter (optional, YYYY-MM-DD)", key="local_research_expiry") or None
 available=status.get("available_models", [])
 preferred=[model for model in ("qwen3:0.6b", "mistral:latest", "gemma4:latest") if model in available]
 if not available:
  st.warning("Ollama is reachable but it reported no installed models.")
  return
 model=st.selectbox("Local model", preferred or available, key="local_research_model")
 question=st.text_area("Research question", value="Summarize the recorded market structure, cite evidence, and propose only a paper-research experiment.", key="local_research_question")
 if st.button("Generate advisory research report", type="primary"):
  with st.spinner("Analyzing selected CQRP evidence locally..."):
   try:
    report=assistant.local_research_report(research, session_id=session, instrument=instrument, expiry=expiry, model=model, question=question, enabled=True)
    st.session_state["local_research_report"]=report
   except RuntimeError as exc:
    st.error(f"Local advisory analysis failed: {exc}")
 report=st.session_state.get("local_research_report")
 if report:
  st.subheader(f"Advisory report — {report.get('model', 'offline')}")
  st.caption(f"Mode: {report.get('mode')} | Training: {report.get('training', 'NONE')}")
  if report.get("accepted"): st.write(report.get("answer"))
  else: st.warning(report.get("answer"))
  st.caption("Evidence IDs: " + ", ".join(report.get("evidence_ids", [])))

def _render_live_fyers_market(st,service,instrument):
 st.title("Market Intelligence")
 st.caption("FYERS is connected for explicit, read-only market-data requests. No broker orders can be sent from CQRP.")
 status=service.fyers_status()
 st.caption(f"FYERS session: {'Ready' if status.ready else 'Not configured'} — {status.reason}")
 st.subheader(f"{instrument} market data")
 if instrument!="NIFTY":
  st.info("This view shows the latest worker-captured data for the selected instrument. The manual FYERS fetch button is currently configured only for NIFTY; multi-index request mappings will be added explicitly rather than guessed.")
 expiry=st.text_input("Expiry (optional)",placeholder="YYYY-MM-DD")
 strikes=st.slider("Strikes on each side of ATM",min_value=1,max_value=20,value=10)
 view=None
 if st.button("Fetch live FYERS option chain",type="primary",disabled=not status.ready or instrument!="NIFTY"):
  view=service.get_live_fyers_market(OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", expiry, strikes))
 elif not status.ready:
  st.info("Add the four CQRP_FYERS_* values in Streamlit Secrets, save, and reboot the app.")
 _render_view(st,view or service.get_latest_fyers_market(instrument=instrument))


def _workstation_main(st, service=None):
    """Feature-flagged Sprints 301–304 shell; legacy Dashboard 2.0 remains untouched."""
    pages = {
        "Live Cockpit": "cockpit",
        "Pre-Market Planner": "planner",
        "Intraday Trail": "trail",
        "Options Intelligence": "options",
        "Paper Portfolio": "portfolio",
        "Research Hub": "research",
        "Analytics": "analytics",
        "Governance": "operations",
    }
    st.sidebar.markdown("## CQRP-DW")
    st.sidebar.caption("CQRP Decision Workstation · PAPER only")
    theme = st.sidebar.radio("Theme", ("Dark", "Light"), horizontal=True, key="cqrp_workstation_theme")
    apply_workstation_theme(st, theme=theme.lower())
    page = st.sidebar.radio("Workstation", list(pages), key="cqrp_workstation_page")
    instrument = st.sidebar.selectbox("Research instrument", ("NIFTY", "BANKNIFTY", "FINNIFTY"), key="cqrp_workstation_instrument")

    def render(active_service):
        dashboard = active_service.get_workstation_dashboard(instrument=instrument)
        render_sidebar_context(st, dashboard)
        destination = pages[page]
        if destination == "cockpit":
            render_live_cockpit(st, dashboard)
        elif destination == "planner":
            st.title("Pre-Market Planner")
            render_conditional_plan(st, dashboard.get("plan") or {}, dashboard.get("premarket_validation"))
            _render_view(st, active_service.get_cqrpdw_dashboard(instrument=instrument))
        elif destination == "trail":
            st.title("Intraday Trail")
            render_structure_map(st, dashboard)
        elif destination == "options":
            st.title("Options Intelligence")
            render_options_intelligence(st, dashboard, compact=False)
        elif destination == "portfolio":
            _render_view(st, active_service.get_portfolio_dashboard(instrument=instrument))
        elif destination == "research":
            _render_view(st, active_service.get_research_knowledge_dashboard())
        elif destination == "analytics":
            _render_view(st, active_service.get_performance_dashboard(instrument=instrument))
        else:
            _render_view(st, active_service.get_operations_dashboard(instrument=instrument))

    def render_with_service():
        active_service = service or DashboardApplicationService()
        owns_service = service is None
        try:
            render(active_service)
        finally:
            if owns_service:
                active_service.close()

    if hasattr(st, "fragment"):
        @st.fragment(run_every=60)
        def auto_refresh_workstation():
            render_with_service()
        auto_refresh_workstation()
    else:
        render_with_service()


if __name__ == "__main__":
    main()
