from dataclasses import dataclass,field
from datetime import datetime,timezone
from types import MappingProxyType
from typing import Any,Mapping
from uuid import uuid4
def now():return datetime.now(timezone.utc).isoformat()
@dataclass(frozen=True)
class Portfolio:
 portfolio_id:str;name:str;owner:str|None;initial_capital:float;created_at:str=field(default_factory=now);created_by:str="PortfolioRiskEngine"
 @classmethod
 def new(cls,**v):v.setdefault("portfolio_id",str(uuid4()));v.setdefault("created_at",now());return cls(**v)
@dataclass(frozen=True)
class RiskDecision:
 decision_id:str;signal_id:str;portfolio_id:str;experiment_id:str|None;risk_version:str;decision:str;requested_quantity:int;approved_quantity:int;capital_required:float;capital_available:float;rejection_reason:str|None;risk_metrics:Mapping[str,Any];created_at:str=field(default_factory=now);created_by:str="PortfolioRiskEngine"
 @classmethod
 def new(cls,**v):v.setdefault("decision_id",str(uuid4()));v.setdefault("created_at",now());v["risk_metrics"]=MappingProxyType(dict(v.get("risk_metrics",{})));return cls(**v)
