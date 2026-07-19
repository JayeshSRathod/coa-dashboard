from src.signal.models import ResearchSignal
from .config import RiskConfig
from .models import RiskDecision
class PortfolioRiskEngine:
 def __init__(self,config=None):self.config=config or RiskConfig()
 def evaluate(self,signal:ResearchSignal,portfolio,*,invested=0.,total_risk=0.,open_positions=0.,daily_pnl=0.,instrument_exposure=0.,experiment_id=None):
  entry=signal.entry_price or 0.;stop=signal.stop_loss
  requested=self.config.fixed_quantity
  if self.config.sizing_method=="FIXED_CAPITAL":requested=int(self.config.fixed_capital/entry) if entry else 0
  elif self.config.sizing_method=="FIXED_RISK":requested=int(self.config.fixed_risk/abs(entry-stop)) if entry and stop is not None and entry!=stop else 0
  elif self.config.sizing_method=="PERCENT_PORTFOLIO":requested=int(portfolio.initial_capital*self.config.portfolio_percent/entry) if entry else 0
  if self.config.sizing_method=="VOLATILITY_BASED":requested=0
  available=max(0.,portfolio.initial_capital*(1-self.config.cash_reserve_percent)-invested)
  capital=entry*requested;risk=abs(entry-(stop if stop is not None else entry))*requested
  reasons=[]
  if signal.signal_type not in {"BUY","SELL"}:reasons.append("signal is not eligible")
  if requested<1:reasons.append("sizing produced zero quantity")
  if daily_pnl<=-self.config.max_daily_loss:reasons.append("daily loss limit breached")
  if open_positions>=self.config.max_open_positions:reasons.append("open-position limit reached")
  if capital>available:reasons.append("insufficient available capital")
  if risk>self.config.max_risk_per_trade or total_risk+risk>self.config.max_portfolio_risk:reasons.append("risk limit breached")
  if instrument_exposure+capital>self.config.max_instrument_exposure:reasons.append("instrument exposure limit breached")
  approved=0 if reasons else requested;decision="APPROVED" if approved else "REJECTED"
  return RiskDecision.new(signal_id=signal.signal_id,portfolio_id=portfolio.portfolio_id,experiment_id=experiment_id,risk_version=self.config.risk_version,decision=decision,requested_quantity=requested,approved_quantity=approved,capital_required=capital if approved else 0.,capital_available=available,rejection_reason="; ".join(reasons) if reasons else None,risk_metrics={"risk":risk,"invested":invested,"total_risk":total_risk,"open_positions":open_positions})
