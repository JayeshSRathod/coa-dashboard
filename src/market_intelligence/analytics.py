"""Deterministic ranking, breadth, sector, theme, and opportunity calculations."""

from __future__ import annotations
from collections import defaultdict
from statistics import fmean

DEFAULT_WEIGHTS={"trend":25,"momentum":20,"volume":15,"oi":15,"risk":10,"validation":10,"portfolio_fit":5}

def calculate_rank(metrics,weights=DEFAULT_WEIGHTS):
 total=sum(weights.values())
 return round(max(0,min(100,sum(float(metrics.get(k,0))*w for k,w in weights.items())/total)),6)

def classify_opportunity(score, horizon="INTRADAY"):
 return "HIGH_CONVICTION" if score>=80 else ("WATCHLIST" if score>=50 else "AVOID")

def market_breadth(records):
 advances=sum(1 for r in records if float(r.get("change_pct",0))>0); declines=sum(1 for r in records if float(r.get("change_pct",0))<0)
 return {"advances":advances,"declines":declines,"advance_decline_ratio":advances/declines if declines else None,"participation":(advances+declines)/len(records)*100 if records else 0}

def sector_strength(records):
 groups=defaultdict(list)
 for r in records: groups[r.get("sector","UNCLASSIFIED")].append(r)
 return [{"sector":sector,"relative_strength":fmean(float(x.get("relative_strength",0)) for x in rows),"leaders":sorted((x["symbol"] for x in rows),key=lambda s:s),"count":len(rows)} for sector,rows in sorted(groups.items())]

def detect_themes(records):
 themes=[]
 by_sector=sector_strength(records)
 for entry in by_sector:
  if entry["relative_strength"]>=70: themes.append({"theme":entry["sector"]+" Strength","sector":entry["sector"],"reason":"relative_strength>=70"})
  if entry["relative_strength"]<=30: themes.append({"theme":entry["sector"]+" Weakness","sector":entry["sector"],"reason":"relative_strength<=30"})
 if any(float(r.get("delivery_spike",0))>=2 for r in records): themes.append({"theme":"High Delivery Buying","reason":"delivery_spike>=2"})
 if any(abs(float(r.get("oi_change",0)))>=20 for r in records): themes.append({"theme":"High OI Activity","reason":"absolute_oi_change>=20"})
 return themes

def generate_watchlists(results):
 horizons=("DAILY","WEEKLY","MONTHLY","LONG_TERM")
 ranked=sorted(results,key=lambda r:(-r.score,r.symbol,r.scanner_id))
 return {h:[r for r in ranked if r.score>=50] for h in horizons}

def alerts_for(previous,current):
 old={r.symbol:r for r in previous}; alerts=[]
 for item in current:
  prior=old.get(item.symbol)
  if prior is None: alerts.append({"type":"WATCHLIST_ADDITION","symbol":item.symbol,"score":item.score})
  elif item.score>prior.score: alerts.append({"type":"SCORE_UPGRADE","symbol":item.symbol,"from":prior.score,"to":item.score})
  elif item.score<prior.score: alerts.append({"type":"SCORE_DOWNGRADE","symbol":item.symbol,"from":prior.score,"to":item.score})
 return alerts
