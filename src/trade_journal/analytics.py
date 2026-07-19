from collections import Counter,defaultdict
from statistics import fmean

def classify_trade(t):
 c=[]
 p=float(t["pnl"])
 c.append("WINNING_TRADE" if p>0 else ("LOSING_TRADE" if p<0 else "SCRATCH_TRADE"))
 if float(t.get("confidence",0))>=70:c.append("HIGH_CONFIDENCE")
 else:c.append("LOW_CONFIDENCE")
 if t.get("holding_period")=="SWING":c.append("SWING_TRADE")
 if t.get("holding_period")=="POSITIONAL":c.append("POSITIONAL_TRADE")
 return tuple(c)

def violations(t,rules):
 out=[]
 if t.get("exit_price") is not None and t.get("stop_loss") is not None and t.get("direction")=="LONG" and float(t["exit_price"])<float(t["stop_loss"]):out.append("STOP_LOSS_EXCEEDED")
 if rules.get("max_quantity") is not None and abs(float(t["quantity"]))>float(rules["max_quantity"]):out.append("POSITION_OVERSIZED")
 if not t.get("validation_complete",False):out.append("VALIDATION_INCOMPLETE")
 return out

def statistics(trades):
 pnls=[float(t["pnl"]) for t in trades];wins=[x for x in pnls if x>0];losses=[x for x in pnls if x<0]
 pf=sum(wins)/abs(sum(losses)) if losses else None
 streak=bestw=bestl=0
 for x in pnls:
  streak=streak+1 if x>0 else 0;bestw=max(bestw,streak)
  streak=streak+1 if x<0 else 0;bestl=max(bestl,streak)
 return {"total_trades":len(trades),"winning_trades":len(wins),"losing_trades":len(losses),"net_pnl":sum(pnls),"win_rate":len(wins)/len(trades)*100 if trades else 0,"average_winner":fmean(wins) if wins else 0,"average_loser":fmean(losses) if losses else 0,"profit_factor":pf,"expectancy":fmean(pnls) if pnls else 0,"max_consecutive_wins":bestw,"max_consecutive_losses":bestl}

def compliance_score(t,violations): return max(0,100-25*len(violations))
