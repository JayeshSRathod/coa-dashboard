"""Composable rule-only market scanners."""

from __future__ import annotations
from .models import ScannerResult

class Scanner:
 scanner_id="BASE"
 def scan(self, records): raise NotImplementedError

class ThresholdScanner(Scanner):
 def __init__(self, scanner_id, metric, threshold, category, direction="ABOVE"):
  self.scanner_id,self.metric,self.threshold,self.category,self.direction=scanner_id,metric,float(threshold),category,direction
 def scan(self, records):
  out=[]
  for row in records:
   value=float(row.get(self.metric,0)); passed=value>=self.threshold if self.direction=="ABOVE" else value<=self.threshold
   if passed: out.append(ScannerResult.new(scanner_id=self.scanner_id,symbol=row["symbol"],asset_class=row.get("asset_class","NSE_EQUITY"),sector=row.get("sector"),category=self.category,score=min(100,max(0,value)),reasons={self.metric:value},metrics=row))
  return out

class ScannerRegistry:
 def __init__(self): self._scanners={}
 def register(self,scanner): self._scanners[scanner.scanner_id]=scanner
 def run(self,records): return [result for scanner_id in sorted(self._scanners) for result in self._scanners[scanner_id].scan(records)]
