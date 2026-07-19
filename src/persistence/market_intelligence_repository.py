"""Append-only repositories for deterministic scanner intelligence."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
from .repository import SQLiteRepository
class _Repo(SQLiteRepository):
 table=""
 def append(self,*,subject_id,payload,fingerprint):
  row=self.connection.execute(f"SELECT record_id FROM {self.table} WHERE fingerprint=?",(fingerprint,)).fetchone()
  if row:return row["record_id"]
  record_id=str(uuid4())
  with self.connection:self.connection.execute(f"INSERT INTO {self.table} VALUES (?,?,?,?,?)",(record_id,subject_id,json.dumps(payload,sort_keys=True,default=str),fingerprint,datetime.now(timezone.utc).isoformat()))
  return record_id
 def list(self):
  return [dict(x)|{"payload":json.loads(x["payload_json"])} for x in self.connection.execute(f"SELECT * FROM {self.table} ORDER BY created_at,record_id").fetchall()]
class ScannerRepository(_Repo): table="scanner_registry"
class ScannerResultRepository(_Repo): table="scanner_results"
class RankingRepository(_Repo): table="scanner_rankings"
class SectorRepository(_Repo): table="sector_intelligence"
class ThemeRepository(_Repo): table="market_themes"
class WatchlistRepository(_Repo): table="ranked_watchlists"
class AlertRepository(_Repo): table="scanner_alerts"
class ScannerPerformanceRepository(_Repo): table="scanner_performance"
