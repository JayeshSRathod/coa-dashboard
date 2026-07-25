"""Dashboard orchestration. Callers inject CQRP services/repositories; no SQL or formulas."""

from __future__ import annotations
from datetime import datetime,timezone
import os
from pathlib import Path

from src.application.fyers_research import FyersResearchService
from src.configuration_console.secrets import CompositeSecretStore, SecretStore
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FyersDataSessionFactory

from .view_models import DashboardView,Freshness
def _fresh(source="local"):return Freshness(source,datetime.now(timezone.utc).isoformat(),"FRESH")
class DashboardApplicationService:
 def __init__(self,providers=None,*,secret_store: SecretStore | None = None,
              fyers_factory: FyersDataSessionFactory | None = None,
              fyers_research: FyersResearchService | None = None):
  self.providers=dict(providers or {})
  self.fyers_factory=fyers_factory or FyersDataSessionFactory(secret_store or CompositeSecretStore())
  self.fyers_research=fyers_research or FyersResearchService(os.getenv("CQRP_RESEARCH_DATABASE_PATH",str(Path.home()/".cqrp"/"research.db")))
 def _view(self,name):
  try:
   data=self.providers.get(name,lambda:{})()
   return DashboardView(name.replace("_"," ").title(),dict(data.get("cards",{})) if isinstance(data,dict) else {},data.get("rows",[]) if isinstance(data,dict) else [],_fresh(name))
  except Exception:return DashboardView(name.replace("_"," ").title(),{},[],Freshness(name,None,"UNAVAILABLE"),"Data unavailable. Check the related CQRP service.")
 def get_home_dashboard(self):return self._view("home")
 def get_market_dashboard(self):return self._view("market")
 def get_scanner_dashboard(self):return self._view("scanner")
 def get_coa_dashboard(self):
  latest=self.fyers_research.latest("NIFTY")
  if latest is None:return DashboardView("Coa Research",{},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"Fetch live FYERS market data to start COA research.")
  if latest.coa_result is None:return DashboardView("Coa Research",{"snapshot_id":latest.snapshot_id},[],Freshness("FYERS",None,"PROCESSING_FAILED"),latest.error or "COA research is unavailable for this snapshot.")
  coa=latest.coa_result; validation=latest.validation_result
  cards={"snapshot_id":latest.snapshot_id,"scenario":coa.scenario,"support":coa.support,"resistance":coa.resistance,"eos":coa.eos,"eor":coa.eor,"risk_mode":coa.risk_mode,"validation_score":validation.overall_score if validation else None,"confidence":validation.confidence_band if validation else None,"validated":validation.is_valid if validation else False,"mode":"RESEARCH_ONLY"}
  return DashboardView("Coa Research",cards,[],Freshness("FYERS",coa.market_timestamp,"FRESH"),latest.error)
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
 def fyers_status(self):
  """Return safe daily-session readiness without exposing a secret value."""
  return self.fyers_factory.status()
 def get_live_fyers_market(self,request: OptionChainRequest):
  """Fetch one explicitly requested, data-only FYERS option-chain snapshot."""
  status=self.fyers_status()
  if not status.ready:
   return DashboardView("FYERS Live Market",{},[],Freshness("FYERS",None,"NOT_CONFIGURED"),status.reason)
  try:
   snapshot=self.fyers_factory.provider().fetch_option_chain(request)
   research=self.fyers_research.process(snapshot)
   rows=[{
    "strike": contract.strike, "type": contract.option_type, "premium": contract.premium,
    "volume": contract.volume, "open_interest": contract.oi, "implied_volatility": contract.iv,
   } for contract in snapshot.contracts]
   cards={"instrument":snapshot.instrument_id,"spot":snapshot.spot,"expiry":snapshot.expiry or "Current expiry",
          "contracts":len(rows),"latency_ms":round(snapshot.latency_ms or 0,1),"research_snapshot_id":research.snapshot_id,"coa_scenario":research.coa_result.scenario if research.coa_result else None,"validation_score":research.validation_result.overall_score if research.validation_result else None,"mode":"DATA_ONLY_PAPER"}
   return DashboardView("FYERS Live Market",cards,rows,Freshness("FYERS",snapshot.captured_at,"FRESH"),research.error)
  except Exception as exc:
   return DashboardView("FYERS Live Market",{},[],Freshness("FYERS",None,"UNAVAILABLE"),
                        f"FYERS market-data request failed: {exc}")
