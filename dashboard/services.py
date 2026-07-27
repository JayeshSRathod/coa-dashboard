"""Dashboard orchestration. Callers inject CQRP services/repositories; no SQL or formulas."""

from __future__ import annotations
from datetime import datetime,timezone
import os
from pathlib import Path

from src.analytics.engine import PerformanceAnalyticsEngine
from src.portfolio_analytics.options import analyze_option_chain
from src.risk.engine import PortfolioRiskEngine
from src.risk.models import Portfolio
from src.scanner.engine import OpportunityScanner
from src.trade_journal.analytics import classify_trade, compliance_score, violations
from src.market_intelligence.state import market_state, technical_confirmation
from src.application.fyers_research import FyersResearchService
from src.configuration_console.secrets import CompositeSecretStore, SecretStore
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FyersDataSessionFactory
from src.research.manual_observations import ManualObservationService
from src.persistence.manual_observation_repository import ManualObservationRepository

from .view_models import DashboardView,Freshness
def _fresh(source="local"):return Freshness(source,datetime.now(timezone.utc).isoformat(),"FRESH")
class DashboardApplicationService:
 def __init__(self,providers=None,*,secret_store: SecretStore | None = None,
              fyers_factory: FyersDataSessionFactory | None = None,
              fyers_research: FyersResearchService | None = None):
  self.providers=dict(providers or {})
  self.fyers_factory=fyers_factory or FyersDataSessionFactory(secret_store or CompositeSecretStore())
  self.fyers_research=fyers_research or FyersResearchService(os.getenv("CQRP_RESEARCH_DATABASE_PATH",str(Path.home()/".cqrp"/"research.db")))
  # Use the same already-migrated read connection as the research service.
  # This avoids creating a second connection in Streamlit/test contexts and
  # preserves the repository-only persistence boundary.
  self.manual_observations=ManualObservationService(
      "", repository=ManualObservationRepository(self.fyers_research.connection)
  )
 def close(self):
  """Release the dashboard's short-lived read connection after a render."""
  self.fyers_research.close()
  self.manual_observations.close()
 def _view(self,name):
  try:
   data=self.providers.get(name,lambda:{})()
   return DashboardView(name.replace("_"," ").title(),dict(data.get("cards",{})) if isinstance(data,dict) else {},data.get("rows",[]) if isinstance(data,dict) else [],_fresh(name))
  except Exception:return DashboardView(name.replace("_"," ").title(),{},[],Freshness(name,None,"UNAVAILABLE"),"Data unavailable. Check the related CQRP service.")
 def get_home_dashboard(self):return self._view("home")
 def get_observation_notes_dashboard(self):
  rows=self.manual_observations.recent(limit=100)
  return DashboardView("Observation Notes",{"count":len(rows),"authority":"MANUAL_APPEND_ONLY"},rows,_fresh("manual_observations"))
 def get_market_dashboard(self):return self._view("market")
 def get_cqrpdw_dashboard(self):
  """The operator's single, read-only CQRP Decision Workstation view."""
  latest=self.fyers_research.latest("NIFTY")
  snapshot=self.fyers_research.latest_snapshot("NIFTY")
  if latest is None or snapshot is None:
   cards={"action":"WAITING_FOR_DATA","mode":"PAPER_ONLY","phase":"AWAITING_SNAPSHOT","rationale":[],"warnings":[],"trade":None,"lifecycle":[]}
   return DashboardView("CQRPDW",cards,[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"Start the local FYERS worker and wait for its first snapshot.")
  coa=latest.coa_result;validation=latest.validation_result;signal=latest.signal
  risk_mode=coa.risk_mode if coa else None
  if risk_mode=="HALT_TRADING":action,reason="NO_TRADE","COA risk mode is HALT_TRADING."
  elif signal is None:action,reason="NO_TRADE","Research signal is unavailable for this snapshot."
  elif signal.signal_type in {"BUY","SELL"}:action,reason=f"PAPER_{signal.signal_type}","CQRP conditions passed; paper lifecycle tracking is active."
  elif signal.signal_type=="WATCHLIST":action,reason="WATCHLIST","A scenario exists, but CQRP evidence is incomplete."
  else:action,reason="NO_TRADE","No configured directional scenario applies."
  trade=self.fyers_research.paper_trade_detail(latest.paper_trade_id) if latest.paper_trade_id else self.fyers_research.current_paper_trade()
  phase=self._paper_phase(trade)
  rationale=list(signal.reasons) if signal else []
  warnings=list(signal.warnings) if signal else []
  if validation:
   rationale.extend(validation.failure_reasons);warnings.extend(validation.warning_reasons)
  rows=[{"check":"COA scenario","result":coa.scenario if coa else "Unavailable"},{"check":"Risk gate","result":risk_mode or "Unavailable"},{"check":"Validation","result":f"{validation.overall_score:.2f} ({validation.confidence_band})" if validation else "Unavailable"},{"check":"Signal","result":signal.signal_type if signal else "Unavailable"},{"check":"Paper lifecycle","result":phase},{"check":"Execution","result":"PAPER ONLY — no FYERS order endpoint"}]
  modules=self._cqrpdw_modules(snapshot,latest,trade)
  cards={"action":action,"reason":reason,"mode":"PAPER_ONLY","phase":phase,"instrument":snapshot.get("instrument"),"spot":snapshot.get("spot"),"scenario":coa.scenario if coa else None,"risk_mode":risk_mode,"support":coa.support if coa else None,"resistance":coa.resistance if coa else None,"eos":coa.eos if coa else None,"eor":coa.eor if coa else None,"validation_score":validation.overall_score if validation else None,"confidence":validation.confidence_band if validation else None,"signal_type":signal.signal_type if signal else None,"signal_id":signal.signal_id if signal else None,"rationale":rationale,"warnings":warnings,"trade":trade,"lifecycle":trade.get("events",[]) if trade else [],"modules":modules}
  return DashboardView("CQRPDW",cards,rows,Freshness("FYERS",str(snapshot.get("market_captured_at")),"FRESH"),latest.error)

 def _cqrpdw_modules(self,snapshot,latest,trade):
  """Compose existing non-order CQRP modules into one workstation read model."""
  signal=latest.signal;coa=latest.coa_result;validation=latest.validation_result
  states=self.fyers_research.paper_states();open_rows=[row for row in states if row["status"] in {"PENDING","OPEN","PARTIALLY_EXITED"}]
  invested=sum(float(row.get("entry") or 0)*int(row.get("quantity_remaining") or 0) for row in open_rows)
  completed=self.fyers_research.completed_paper_trades()
  performance=PerformanceAnalyticsEngine().scenario_analysis(completed)
  stored_risk=self.fyers_research.risk_decision_for_signal(signal)
  risk=None
  if stored_risk:
   risk={"decision":stored_risk.decision,"requested_quantity":stored_risk.requested_quantity,"approved_quantity":stored_risk.approved_quantity,"capital_required":stored_risk.capital_required,"capital_available":stored_risk.capital_available,"reason":stored_risk.rejection_reason,"metrics":dict(stored_risk.risk_metrics)}
  chain=[]
  for row in snapshot.get("option_chain") or []:
   chain.extend(({"strike":row.get("Strike"),"option_type":"CALL","oi":row.get("Call_OI",0),"bid":row.get("Call_LTP",0),"ask":row.get("Call_LTP",0)},{"strike":row.get("Strike"),"option_type":"PUT","oi":row.get("Put_OI",0),"bid":row.get("Put_LTP",0),"ask":row.get("Put_LTP",0)}))
  options=analyze_option_chain(chain,float(snapshot.get("spot") or 0)) if chain else {}
  quality=float(validation.overall_score if validation else 0)
  candidate=OpportunityScanner().rank([{"instrument_id":snapshot.get("instrument","NIFTY"),"price":snapshot.get("spot",0),"coa":quality,"trend_score":100 if signal and signal.direction=="BUY" else 0,"momentum":quality,"liquidity":quality,"volume":quality,"relative_strength":quality,"risk":100 if risk and risk["decision"]!="REJECTED" else 0,"volatility":50,"quality":quality,"tradable":signal is not None}])
  journal=[]
  for item in completed[-20:]:
   row={"trade_id":item.trade_id,"pnl":item.realized_pnl,"confidence":item.confidence_score or 0,"quantity":item.quantity,"direction":"LONG" if item.direction=="BUY" else "SHORT","exit_price":item.exit_price,"stop_loss":None,"validation_complete":True}
   issues=violations(row,{"max_quantity":1});journal.append({"trade_id":item.trade_id,"scenario":item.scenario,"pnl":item.realized_pnl,"categories":list(classify_trade(row)),"violations":issues,"compliance_score":compliance_score(row,issues)})
  captured=str(snapshot.get("market_captured_at") or "")
  try:age=round((datetime.now(timezone.utc)-datetime.fromisoformat(captured.replace("Z","+00:00"))).total_seconds(),1)
  except ValueError:age=None
  feed=[]
  for instrument in self.fyers_research.instruments():
   item=self.fyers_research.latest(instrument); latest_snapshot=self.fyers_research.latest_snapshot(instrument)
   if item is None or latest_snapshot is None:continue
   history=self.fyers_research.spot_history(instrument)
   state=market_state(history); technical=technical_confirmation(history)
   item_signal=item.signal
   feed.append({"instrument":instrument,"spot":latest_snapshot.get("spot"),"signal":item_signal.signal_type if item_signal else "UNAVAILABLE","direction":item_signal.direction if item_signal else None,"confidence":item_signal.confidence_score if item_signal else 0,"scenario":item.coa_result.scenario if item.coa_result else None,"market_state":state["state"],"technical":technical["status"],"technical_bias":technical.get("bias"),"updated_at":latest_snapshot.get("market_captured_at")})
  feed.sort(key=lambda item:(-(float(item["confidence"] or 0)),str(item["instrument"])))
  primary_history=self.fyers_research.spot_history(str(snapshot.get("instrument") or "NIFTY"))
  return {"market_state":market_state(primary_history)|{"coa_scenario":coa.scenario if coa else None,"risk_mode":coa.risk_mode if coa else None},"technical_confirmation":technical_confirmation(primary_history),"decision_feed":feed,"scanner":[candidate.__dict__ for candidate in candidate],"risk":risk,"options_analytics":options,"performance":{"metrics":dict(performance.metrics),"by_scenario":dict(performance.groups)},"trade_journal":journal,"operations":{"worker":"LOCAL_WORKER_REQUIRED","snapshot_age_seconds":age,"data_quality":snapshot.get("data_quality_status"),"open_paper_trades":len(open_rows),"completed_paper_trades":len(completed),"recent_worker_cycles":self.fyers_research.worker_events()}}

 @staticmethod
 def _paper_phase(trade):
  if not trade:return "NO_ACTIVE_PAPER_TRADE"
  status=str(trade.get("status"))
  if status=="PENDING":return "ENTRY_PENDING"
  if status=="OPEN":return "IN_TRADE — MONITOR T1 / STOP"
  if status=="PARTIALLY_EXITED":return "T1 COMPLETED — MANAGE T2 / TRAIL"
  if status=="CLOSED":return f"EXITED — {trade.get('exit_reason') or 'COMPLETED'}"
  return status
 def get_decision_dashboard(self):
  latest=self.fyers_research.latest("NIFTY")
  snapshot=self.fyers_research.latest_snapshot("NIFTY")
  if latest is None or snapshot is None:return DashboardView("Decision Dashboard",{"action":"WAITING_FOR_DATA","mode":"PAPER_ONLY"},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"The local worker has not captured a FYERS snapshot yet.")
  coa=latest.coa_result; validation=latest.validation_result; signal=latest.signal
  risk_mode=coa.risk_mode if coa else None
  if risk_mode == "HALT_TRADING":action,reason="NO_TRADE","COA risk mode is HALT_TRADING."
  elif signal is None:action,reason="NO_TRADE","No research signal is available."
  elif signal.signal_type in {"BUY","SELL"}:action,reason=f"PAPER_{signal.signal_type}_CANDIDATE","Configured scenario and validation thresholds are satisfied; PAPER tracking only."
  elif signal.signal_type == "WATCHLIST":action,reason="WATCHLIST","Scenario is present but one or more research checks did not pass."
  else:action,reason="NO_TRADE","No configured directional scenario applies."
  cards={"action":action,"reason":reason,"mode":"PAPER_ONLY","instrument":snapshot.get("instrument"),"spot":snapshot.get("spot"),"scenario":coa.scenario if coa else None,"risk_mode":risk_mode,"support":coa.support if coa else None,"resistance":coa.resistance if coa else None,"eos":coa.eos if coa else None,"eor":coa.eor if coa else None,"validation_score":validation.overall_score if validation else None,"confidence":validation.confidence_band if validation else None,"signal_type":signal.signal_type if signal else None,"paper_trade_id":latest.paper_trade_id}
  rows=[{"check":"COA scenario","result":coa.scenario if coa else "Unavailable"},{"check":"Risk gate","result":risk_mode or "Unavailable"},{"check":"Validation","result":f"{validation.overall_score:.2f} ({validation.confidence_band})" if validation else "Unavailable"},{"check":"Research signal","result":signal.signal_type if signal else "Unavailable"},{"check":"Execution","result":"PAPER ONLY — no FYERS order endpoint"}]
  return DashboardView("Decision Dashboard",cards,rows,Freshness("FYERS",str(snapshot.get("market_captured_at")),"FRESH"),None)
 def get_latest_fyers_market(self):
  snapshot=self.fyers_research.latest_snapshot("NIFTY")
  if snapshot is None:return DashboardView("FYERS Live Market",{},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"The local FYERS worker has not captured a snapshot yet.")
  rows=snapshot.get("option_chain") or []
  cards={"instrument":snapshot.get("instrument"),"spot":snapshot.get("spot"),"expiry":snapshot.get("expiry") or "Current expiry","contracts":len(rows),"snapshot_id":snapshot.get("snapshot_id"),"mode":"DATA_ONLY_PAPER"}
  return DashboardView("FYERS Live Market",cards,rows,Freshness(str(snapshot.get("market_source") or "FYERS"),str(snapshot.get("market_captured_at")),"FRESH"))
 def get_scanner_dashboard(self):
  latest=self.fyers_research.latest("NIFTY")
  if latest is None:return DashboardView("Scanner",{},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"Fetch live FYERS market data to start scanner research.")
  if latest.signal is None:return DashboardView("Scanner",{"snapshot_id":latest.snapshot_id},[],Freshness("FYERS",None,"PROCESSING_FAILED"),latest.error or "Research signal is unavailable for this snapshot.")
  signal=latest.signal
  cards={"snapshot_id":latest.snapshot_id,"signal_type":signal.signal_type,"direction":signal.direction,"scenario":signal.scenario,"confidence_score":signal.confidence_score,"confidence_band":signal.confidence_band,"entry":signal.entry_price,"target_1":signal.target_1,"target_2":signal.target_2,"mode":"RESEARCH_ONLY"}
  rows=[{"reason":reason} for reason in signal.reasons]
  return DashboardView("Scanner",cards,rows,Freshness("FYERS",signal.created_at,"FRESH"),latest.error)
 def get_coa_dashboard(self):
  latest=self.fyers_research.latest("NIFTY")
  if latest is None:return DashboardView("Coa Research",{},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"Fetch live FYERS market data to start COA research.")
  if latest.coa_result is None:return DashboardView("Coa Research",{"snapshot_id":latest.snapshot_id},[],Freshness("FYERS",None,"PROCESSING_FAILED"),latest.error or "COA research is unavailable for this snapshot.")
  coa=latest.coa_result; validation=latest.validation_result
  events=self.fyers_research.dynamic_events("NIFTY", limit=50)
  cards={"snapshot_id":latest.snapshot_id,"scenario":coa.scenario,"support":coa.support,"resistance":coa.resistance,"eos":coa.eos,"eor":coa.eor,"risk_mode":coa.risk_mode,"validation_score":validation.overall_score if validation else None,"confidence":validation.confidence_band if validation else None,"validated":validation.is_valid if validation else False,"mode":"RESEARCH_ONLY"}
  cards["dynamic_structure_events"] = len(events)
  rows=[{"occurred_at":event.get("occurred_at"),"event":event.get("event_type"),"key":event.get("event_key"),"scenario_track":event.get("scenario_track"),"outcome":event.get("outcome_state"),"details":event.get("payload")} for event in events]
  return DashboardView("Coa Research",cards,rows,Freshness("FYERS",coa.market_timestamp,"FRESH"),latest.error)
 def get_strategy_lab_dashboard(self):return self._view("strategy_lab")
 def get_research_knowledge_dashboard(self):return self._view("research_knowledge")
 def get_portfolio_dashboard(self):
  rows=self.fyers_research.paper_states()
  if not rows:return DashboardView("Portfolio",{"mode":"PAPER_ONLY","open_positions":0,"realized_pnl":0.0},[],Freshness("CQRP",None,"AWAITING_SIGNAL"),"No directional research signal has created a paper trade yet.")
  open_positions=sum(row["status"] in {"PENDING","OPEN","PARTIALLY_EXITED"} for row in rows)
  realized=sum(float(row["realized_pnl"] or 0) for row in rows)
  return DashboardView("Portfolio",{"mode":"PAPER_ONLY","open_positions":open_positions,"paper_trades":len(rows),"realized_pnl":round(realized,2)},rows,Freshness("CQRP",None,"FRESH"))
 def get_options_dashboard(self):
  snapshot=self.fyers_research.latest_snapshot("NIFTY")
  if snapshot is None:return DashboardView("Options Analytics",{},[],Freshness("FYERS",None,"AWAITING_SNAPSHOT"),"Awaiting a FYERS option-chain snapshot.")
  chain=[]
  for row in snapshot.get("option_chain") or []:
   chain.extend(({"strike":row.get("Strike"),"option_type":"CALL","oi":row.get("Call_OI",0),"bid":row.get("Call_LTP",0),"ask":row.get("Call_LTP",0)}, {"strike":row.get("Strike"),"option_type":"PUT","oi":row.get("Put_OI",0),"bid":row.get("Put_LTP",0),"ask":row.get("Put_LTP",0)}))
  analysis=analyze_option_chain(chain,float(snapshot.get("spot") or 0)) if chain else {}
  cards={"mode":"DATA_ONLY_PAPER","spot":snapshot.get("spot"),"atm":analysis.get("atm"),"pcr":analysis.get("pcr"),"call_oi":analysis.get("call_oi"),"put_oi":analysis.get("put_oi"),"average_spread":analysis.get("average_spread")}
  return DashboardView("Options Analytics",cards,chain,Freshness("FYERS",str(snapshot.get("market_captured_at")),"FRESH"))
 def get_trade_journal_dashboard(self):
  trades=self.fyers_research.completed_paper_trades()
  if not trades:return DashboardView("Trade Journal",{"mode":"PAPER_ONLY","completed_trades":0},[],Freshness("CQRP",None,"AWAITING_CLOSED_TRADE"),"Journal entries appear after a paper trade closes.")
  rows=[]
  for trade in trades:
   record={"pnl":trade.realized_pnl,"confidence":trade.confidence_score or 0,"quantity":trade.quantity,"direction":"LONG" if trade.direction=="BUY" else "SHORT","exit_price":trade.exit_price,"stop_loss":None,"validation_complete":True}
   issues=violations(record,{"max_quantity":1})
   rows.append({"trade_id":trade.trade_id,"instrument":trade.instrument,"scenario":trade.scenario,"pnl":trade.realized_pnl,"categories":list(classify_trade(record)),"violations":issues,"compliance_score":compliance_score(record,issues)})
  return DashboardView("Trade Journal",{"mode":"PAPER_ONLY","completed_trades":len(rows)},rows,_fresh("CQRP"))
 def get_performance_dashboard(self):
  trades=self.fyers_research.completed_paper_trades()
  report=PerformanceAnalyticsEngine().report(trades,report_type="PAPER_PERFORMANCE")
  cards={"mode":"PAPER_ONLY"}|dict(report.metrics)
  return DashboardView("Performance",cards,PerformanceAnalyticsEngine().equity_curve(trades),_fresh("CQRP"),None if trades else "Performance metrics will populate after closed paper trades.")
 def get_execution_dashboard(self):
  rows=self.fyers_research.paper_states()
  active=sum(row["status"] in {"PENDING","OPEN","PARTIALLY_EXITED"} for row in rows)
  return DashboardView("Execution (Paper Only)",{"mode":"PAPER_ONLY","active_paper_trades":active,"total_paper_trades":len(rows),"broker_orders":0},rows,_fresh("CQRP"),None if rows else "No paper execution lifecycle exists yet.")
 def get_operations_dashboard(self):
  health=self.fyers_research.market_health();events=self.fyers_research.system_events()
  failures=[event for event in events if str(event.get("severity","")) in {"ERROR","CRITICAL"}]
  cards={"mode":"OBSERVATION_ONLY","provider_health_records":len(health),"recent_events":len(events),"recent_failures":len(failures),"worker_status":"DEGRADED" if failures else "HEALTHY"}
  rows=[{"occurred_at":event.get("occurred_at"),"event_type":event.get("event_type"),"severity":event.get("severity"),"instrument":event.get("instrument"),"details":event.get("payload")} for event in events]
  return DashboardView("Operations Center",cards,rows,_fresh("CQRP"),None if events else "No operational events have been recorded yet.")
 def get_alert_dashboard(self):
  events=self.fyers_research.system_events()
  rows=[{"occurred_at":event.get("occurred_at"),"severity":event.get("severity"),"event_type":event.get("event_type"),"instrument":event.get("instrument"),"details":event.get("payload")} for event in events if str(event.get("severity","")) in {"ERROR","CRITICAL","WARNING"}]
  return DashboardView("Alerts",{"active_alerts":len(rows),"mode":"OBSERVATION_ONLY"},rows,_fresh("CQRP"),None if rows else "No persisted CQRP warning or error alerts are active.")
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
          "contracts":len(rows),"latency_ms":round(snapshot.latency_ms or 0,1),"research_snapshot_id":research.snapshot_id,"coa_scenario":research.coa_result.scenario if research.coa_result else None,"validation_score":research.validation_result.overall_score if research.validation_result else None,"signal_type":research.signal.signal_type if research.signal else None,"paper_trade_id":research.paper_trade_id,"mode":"DATA_ONLY_PAPER"}
   return DashboardView("FYERS Live Market",cards,rows,Freshness("FYERS",snapshot.captured_at,"FRESH"),research.error)
  except Exception as exc:
   return DashboardView("FYERS Live Market",{},[],Freshness("FYERS",None,"UNAVAILABLE"),
                        f"FYERS market-data request failed: {exc}")
