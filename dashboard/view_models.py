from dataclasses import dataclass,asdict
from datetime import datetime,timezone
@dataclass(frozen=True)
class Freshness: source:str; updated_at:str|None; status:str
@dataclass(frozen=True)
class DashboardView: title:str; cards:dict; rows:list; freshness:Freshness; error:str|None=None
def serialise(value): return asdict(value) if hasattr(value,"__dataclass_fields__") else value
def mask_secret(value): return "********" if value else ""
