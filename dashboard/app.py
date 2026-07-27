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
from src.market_data.contracts import OptionChainRequest
PAGES={"CQRPDW":"get_cqrpdw_dashboard","Market Intelligence":"get_market_dashboard","Scanner":"get_scanner_dashboard","COA Research":"get_coa_dashboard","Strike Activity":"get_dynamic_walls_dashboard","Strategy Lab":"get_strategy_lab_dashboard","Research Knowledge":"get_research_knowledge_dashboard","Portfolio":"get_portfolio_dashboard","Options Analytics":"get_options_dashboard","Trade Journal":"get_trade_journal_dashboard","Performance":"get_performance_dashboard","Execution":"get_execution_dashboard","Operations Center":"get_operations_dashboard","Alerts":"get_alert_dashboard","Observation Notes":"get_observation_notes_dashboard","Configuration":"get_configuration_dashboard"}
INSTRUMENT_SCOPED_PAGES={"CQRPDW","Market Intelligence","Scanner","COA Research","Strike Activity","Portfolio","Options Analytics","Trade Journal","Performance","Execution","Operations Center","Alerts"}
def main(service=None):
    import streamlit as st

    st.set_page_config(page_title="CQRP Dashboard 2.0", layout="wide")
    page = st.sidebar.selectbox("CQRP Navigation", list(PAGES))
    instrument = st.sidebar.selectbox("Research instrument", ["NIFTY", "BANKNIFTY", "FINNIFTY"], help="Shared scope for all market-facing pages.")
    if page == "Configuration":
        render_configuration_page()
        return

    def render_page(active_service):
        if page == "Observation Notes":
            render_observation_page(active_service.manual_observations)
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
 event_types=service.available_dynamic_event_types(instrument, selected_session)
 selected_events=st.multiselect("Structure events", event_types, default=event_types, key="coa_event_types")
 view=service.get_coa_dashboard(instrument=instrument, session_id=selected_session, event_types=tuple(selected_events))
 _render_view(st, view)
 st.caption("Events include COA1/COA2 scenario track, moving levels, breakout/retest evidence, and linked validation/risk/paper outcome IDs. Use Strike Activity for CE/PE strike-wall history.")

def _render_strike_activity(st, service, instrument):
 sessions=service.available_sessions(instrument)
 session=st.selectbox("Session", ["All sessions", *sessions], key="walls_session")
 view=service.get_dynamic_walls_dashboard(instrument=instrument, session_id=None if session=="All sessions" else session)
 _render_view(st, view)
 st.caption("Each row is a top-three CE/PE Volume or OI wall at a specific strike. This is the auditable strike-level evidence behind support/resistance migration.")

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
if __name__=="__main__":main()
