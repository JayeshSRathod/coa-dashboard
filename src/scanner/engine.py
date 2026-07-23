from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence
@dataclass(frozen=True)
class DecisionCandidate:
 candidate_id:str; instrument_id:str; horizon:str; score:float; trend:str; confidence:float; entry_zone:float; stop_zone:float; target1:float; target2:float; coa_alignment:float; created_at:str
class OpportunityScanner:
 """Deterministic scanner: candidates only; it never creates orders."""
 def rank(self, universe:Sequence[Mapping[str,object]], horizon:str="SWING")->list[DecisionCandidate]:
  out=[]
  for row in universe:
   if not row.get("tradable",True) or float(row.get("liquidity",0))<50 or float(row.get("quality",0))<50: continue
   score=round(.25*float(row.get("coa",0))+.2*float(row.get("trend_score",0))+.15*float(row.get("momentum",0))+.1*float(row.get("liquidity",0))+.1*float(row.get("volume",0))+.1*float(row.get("relative_strength",0))+.05*float(row.get("risk",0))+.05*float(row.get("volatility",0)),2)
   price=float(row.get("price",0)); trend="BULLISH" if float(row.get("trend_score",0))>=50 else "BEARISH"; out.append(DecisionCandidate(str(row["instrument_id"])+":"+horizon,horizon=horizon,instrument_id=str(row["instrument_id"]),score=score,trend=trend,confidence=score,entry_zone=price,stop_zone=round(price*.97,2),target1=round(price*1.03,2),target2=round(price*1.06,2),coa_alignment=float(row.get("coa",0)),created_at=datetime.now(timezone.utc).isoformat()))
  return sorted(out,key=lambda x:(-x.score,x.instrument_id))
