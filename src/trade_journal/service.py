from hashlib import sha256
import json
from src.research.observability import emit_snapshot_event
from .analytics import classify_trade,violations,statistics,compliance_score
def _fp(x):return sha256(json.dumps(x,sort_keys=True,default=str).encode()).hexdigest()
class TradeJournalService:
 def __init__(self,repositories,logger=None):self.repositories,self.logger=repositories,logger
 def create_trade_journal(self,trade,rules=None):
  rules=rules or {}; categories=classify_trade(trade); issues=violations(trade,rules); score=compliance_score(trade,issues)
  entry=dict(trade)|{"categories":categories,"violations":issues,"compliance_score":score}
  jid=self.repositories["journal"].append(trade["trade_id"],entry,_fp(entry))
  self.repositories["compliance"].append(trade["trade_id"],{"score":score,"violations":issues},_fp({"id":trade["trade_id"],"issues":issues}))
  if self.logger:emit_snapshot_event(self.logger,"trade_journal_created",trade_id=trade["trade_id"],journal_id=jid)
  return jid,entry
 def calculate_trade_statistics(self):
  entries=[x["payload"] for x in self.repositories["journal"].list()];result=statistics(entries);self.repositories["statistics"].append("LIFETIME",result,_fp(result));return result
 def update_learning_repository(self):
  entries=[x["payload"] for x in self.repositories["journal"].list()];groups={}
  for key in ("strategy","instrument","market","sector"):
   d={}
   for e in entries:d.setdefault(e.get(key,"UNKNOWN"),[]).append(e)
   groups[key]={k:statistics(v) for k,v in sorted(d.items())}
  self.repositories["learning"].append("ALL",groups,_fp(groups));return groups
 def generate_report(self,period):
  entries=[x["payload"] for x in self.repositories["journal"].list()];payload={"period":period,"statistics":statistics(entries),"trades":len(entries)};self.repositories["report"].append(period,payload,_fp(payload));return payload
 def find_by_strategy(self,value):return [x["payload"] for x in self.repositories["journal"].list() if x["payload"].get("strategy")==value]
 def find_rule_violations(self):return [x["payload"] for x in self.repositories["journal"].list() if x["payload"]["violations"]]
