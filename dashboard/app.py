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
from dashboard.view_models import serialise
from dashboard.configuration_page import render_configuration_page
from src.market_data.contracts import OptionChainRequest
PAGES={"Home":"get_home_dashboard","Market Intelligence":"get_market_dashboard","Scanner":"get_scanner_dashboard","COA Research":"get_coa_dashboard","Strategy Lab":"get_strategy_lab_dashboard","Research Knowledge":"get_research_knowledge_dashboard","Portfolio":"get_portfolio_dashboard","Options Analytics":"get_options_dashboard","Trade Journal":"get_trade_journal_dashboard","Performance":"get_performance_dashboard","Execution":"get_execution_dashboard","Operations Center":"get_operations_dashboard","Alerts":"get_alert_dashboard","Configuration":"get_configuration_dashboard"}
def main(service=None):
 import streamlit as st
 st.set_page_config(page_title="CQRP Dashboard 2.0",layout="wide");service=service or DashboardApplicationService()
 page=st.sidebar.selectbox("CQRP Navigation",list(PAGES));
 if page=="Configuration":
  render_configuration_page();return
 if page=="Market Intelligence":
  _render_live_fyers_market(st,service);return
 view=getattr(service,PAGES[page])()
 _render_view(st,view)

def _render_view(st,view):
 st.title(view.title);st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 if view.error:st.warning(view.error)
 if view.cards:st.json(view.cards)
 if view.rows:st.dataframe(view.rows,use_container_width=True)
 else:st.info("No data is currently available for this view.")

def _render_live_fyers_market(st,service):
 st.title("Market Intelligence")
 st.caption("FYERS is connected for explicit, read-only market-data requests. No broker orders can be sent from CQRP.")
 status=service.fyers_status()
 st.caption(f"FYERS session: {'Ready' if status.ready else 'Not configured'} — {status.reason}")
 symbol=st.selectbox("Instrument",["NIFTY 50"],format_func=lambda _:"NIFTY 50 (NSE)")
 expiry=st.text_input("Expiry (optional)",placeholder="YYYY-MM-DD")
 strikes=st.slider("Strikes on each side of ATM",min_value=1,max_value=20,value=10)
 if st.button("Fetch live FYERS option chain",type="primary",disabled=not status.ready):
  view=service.get_live_fyers_market(OptionChainRequest("NIFTY", "NSE:NIFTY50-INDEX", expiry, strikes))
  _render_view(st,view)
 elif not status.ready:
  st.info("Add the four CQRP_FYERS_* values in Streamlit Secrets, save, and reboot the app.")
if __name__=="__main__":main()
