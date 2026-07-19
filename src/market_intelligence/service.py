from hashlib import sha256
import json
from src.research.observability import emit_snapshot_event
from .analytics import calculate_rank, market_breadth, sector_strength, detect_themes, generate_watchlists, alerts_for

def _fp(x): return sha256(json.dumps(x,sort_keys=True,default=str).encode()).hexdigest()

class MarketIntelligenceService:
 def __init__(self, registry,repositories,logger=None): self.registry,self.repositories,self.logger=registry,repositories,logger
 def run_scanner(self,records):
  results=self.registry.run(records)
  for r in results:self.repositories["result"].append(subject_id=r.symbol,payload=r.__dict__,fingerprint=_fp(r.__dict__))
  if self.logger:emit_snapshot_event(self.logger,"scanner_executed",results=len(results))
  return results
 def calculate_rank(self,metrics): return calculate_rank(metrics)
 def analyze_market_breadth(self,records): return market_breadth(records)
 def analyze_sector_strength(self,records): return sector_strength(records)
 def detect_market_themes(self,records): return detect_themes(records)
 def generate_watchlists(self,results):
  lists=generate_watchlists(results)
  for horizon,items in lists.items():self.repositories["watchlist"].append(subject_id=horizon,payload={"horizon":horizon,"symbols":[r.symbol for r in items]},fingerprint=_fp([horizon]+[r.scanner_result_id for r in items]))
  return lists
 def generate_alerts(self,previous,current): return alerts_for(previous,current)
