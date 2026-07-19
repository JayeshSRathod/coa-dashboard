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
PAGES={"Home":"get_home_dashboard","Market Intelligence":"get_market_dashboard","Scanner":"get_scanner_dashboard","COA Research":"get_coa_dashboard","Strategy Lab":"get_strategy_lab_dashboard","Research Knowledge":"get_research_knowledge_dashboard","Portfolio":"get_portfolio_dashboard","Options Analytics":"get_options_dashboard","Trade Journal":"get_trade_journal_dashboard","Performance":"get_performance_dashboard","Execution":"get_execution_dashboard","Operations Center":"get_operations_dashboard","Alerts":"get_alert_dashboard","Configuration":"get_configuration_dashboard"}
def main(service=None):
 import streamlit as st
 st.set_page_config(page_title="CQRP Dashboard 2.0",layout="wide");service=service or DashboardApplicationService()
 page=st.sidebar.selectbox("CQRP Navigation",list(PAGES));view=getattr(service,PAGES[page])()
 st.title(view.title);st.caption(f"Source: {view.freshness.source} | Status: {view.freshness.status} | Updated: {view.freshness.updated_at}")
 if view.error:st.warning(view.error)
 if view.cards:st.json(view.cards)
 if view.rows:st.dataframe(view.rows,use_container_width=True)
 else:st.info("No data is currently available for this view.")
if __name__=="__main__":main()
