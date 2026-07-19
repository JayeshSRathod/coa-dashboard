import csv,json
from io import StringIO
def export_json(rows):return json.dumps(rows,default=str,sort_keys=True)
def export_csv(rows):
 rows=list(rows);out=StringIO()
 if not rows:return ""
 keys=sorted({k for row in rows for k in row});w=csv.DictWriter(out,fieldnames=keys);w.writeheader();w.writerows(rows);return out.getvalue()
