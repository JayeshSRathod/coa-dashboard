from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from uuid import uuid4

def _now(): return datetime.now(timezone.utc).isoformat()
def _frozen(value=None): return MappingProxyType(dict(value or {}))

@dataclass(frozen=True)
class ScannerResult:
 scanner_result_id:str; scanner_id:str; symbol:str; asset_class:str; score:float; category:str
 sector:str|None=None; reasons:object=field(default_factory=_frozen); metrics:object=field(default_factory=_frozen); occurred_at:str=field(default_factory=_now)
 @classmethod
 def new(cls,**values):
  values.setdefault("scanner_result_id",str(uuid4())); values["reasons"]=_frozen(values.get("reasons")); values["metrics"]=_frozen(values.get("metrics")); return cls(**values)
