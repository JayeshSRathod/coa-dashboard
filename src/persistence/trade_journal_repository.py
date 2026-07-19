import json
from datetime import datetime,timezone
from uuid import uuid4
from .repository import SQLiteRepository
class _Repo(SQLiteRepository):
 table=""
 def append(self,subject_id,payload,fingerprint):
  row=self.connection.execute(f"SELECT record_id FROM {self.table} WHERE fingerprint=?",(fingerprint,)).fetchone()
  if row:return row["record_id"]
  i=str(uuid4())
  with self.connection:self.connection.execute(f"INSERT INTO {self.table} VALUES (?,?,?,?,?)",(i,subject_id,json.dumps(payload,sort_keys=True,default=str),fingerprint,datetime.now(timezone.utc).isoformat()))
  return i
 def list(self):
  return [dict(x)|{"payload":json.loads(x["payload_json"])} for x in self.connection.execute(f"SELECT * FROM {self.table} ORDER BY created_at,record_id").fetchall()]
class TradeJournalRepository(_Repo):table="trade_journals"
class LearningRepository(_Repo):table="trade_learning"
class PerformanceRepository(_Repo):table="trade_performance"
class ComplianceRepository(_Repo):table="trade_compliance"
class TimelineRepository(_Repo):table="trade_timelines"
class StatisticsRepository(_Repo):table="trade_statistics"
class ReportRepository(_Repo):table="trade_reports"
