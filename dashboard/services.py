"""Dashboard orchestration. Callers inject CQRP services/repositories; no SQL or formulas."""

from __future__ import annotations
from datetime import datetime,timezone
from .view_models import DashboardView,Freshness
def _fresh(source="local"):return Freshness(source,datetime.now(timezone.utc).isoformat(),"FRESH")
class DashboardApplicationService:
 def __init__(self,providers=None):self.providers=dict(providers or {})
 def _view(self,name):
  try:
   data=self.providers.get(name,lambda:{})()
   return DashboardView(name.replace("_"," ").title(),dict(data.get("cards",{})) if isinstance(data,dict) else {},data.get("rows",[]) if isinstance(data,dict) else [],_fresh(name))
  except Exception:return DashboardView(name.replace("_"," ").title(),{},[],Freshness(name,None,"UNAVAILABLE"),"Data unavailable. Check the related CQRP service.")
 def get_home_dashboard(self):return self._view("home")
 def get_market_dashboard(self):return self._view("market")
 def get_scanner_dashboard(self):return self._view("scanner")
 def get_coa_dashboard(self):return self._view("coa")
 def get_strategy_lab_dashboard(self):return self._view("strategy_lab")
 def get_research_knowledge_dashboard(self):return self._view("research_knowledge")
 def get_portfolio_dashboard(self):return self._view("portfolio")
 def get_options_dashboard(self):return self._view("options")
 def get_trade_journal_dashboard(self):return self._view("trade_journal")
 def get_performance_dashboard(self):return self._view("performance")
 def get_execution_dashboard(self):return self._view("execution")
 def get_operations_dashboard(self):return self._view("operations")
 def get_alert_dashboard(self):return self._view("alerts")
 def get_configuration_dashboard(self):return self._view("configuration")
