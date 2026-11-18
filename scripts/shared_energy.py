"""Reuse the approved Energy plant register; do not collect NVE twice."""
import json, math
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
URL="https://energy.nordl.dev/data/hydro-plants-v1.json"
SOURCE="https://api.nve.no/web/Powerplant/GetHydroPowerPlantsInOperation"
LICENSE="https://data.norge.no/nlod/"
ZONES={f"NO{i}" for i in range(1,6)}
OUT="data/shared-energy-context.json"
NOTICE="Reported nameplate capacity by bidding zone; not actual production, reservoir fill, company exposure or equity-adjusted ownership."
def parse(d):
    if d.get("schema_version")!=1 or d.get("source")!=SOURCE or d.get("license")!=LICENSE:
        raise ValueError("unapproved source or schema")
    t=datetime.fromisoformat(d["generated"].replace("Z","+00:00"))
    if t.tzinfo is None or t>datetime.now(timezone.utc):
        raise ValueError("invalid source date")
    rows=d["rows"]
    if not isinstance(rows,list) or not rows or len(rows)>20000:
        raise ValueError("invalid register size")
    zones={k:{"zone":k,"plants":0,"capacityRecords":0,"capacityMW":0.0} for k in ZONES}
    seen=set();missing=0
    for row in rows:
        key=row.get("id")
        if isinstance(key,bool) or not isinstance(key,int) or key in seen or row.get("zone") not in ZONES:
            raise ValueError("invalid or duplicate plant")
        seen.add(key);z=zones[row["zone"]];z["plants"]+=1
        val=row.get("capacity_mw")
        if isinstance(val,(int,float)) and not isinstance(val,bool) and math.isfinite(val) and val>=0:
            z["capacityRecords"]+=1;z["capacityMW"]+=val
        else:missing+=1
    if any(not z["plants"] or not z["capacityRecords"] for z in zones.values()):
        raise ValueError("incomplete zone coverage")
    for z in zones.values():z["capacityMW"]=round(z["capacityMW"],4)
    return {"schemaVersion":1,"sourceGenerated":d["generated"],"sourceUrl":URL,"originalSource":SOURCE,
            "license":LICENSE,"attribution":"NVE; Nordl normalization","plants":len(rows),
            "missingCapacity":missing,"zones":[zones[k] for k in sorted(zones)],"notice":NOTICE}
def fetch():
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch research (https://stocks.nordl.dev)"}),timeout=15) as r:
        data=r.read(8_000_001)
    if len(data)>8_000_000:raise ValueError("response too large")
    return json.loads(data)
def build(root=ROOT,load=fetch,now=None):
    now=now or datetime.now(timezone.utc)
    path=root/OUT
    try:old=json.loads(path.read_text(encoding="utf8"))
    except (ValueError,OSError):old={}
    if str(old.get("lastAttempt",""))[:10]==now.date().isoformat():return old
    try:
        new=parse(load())
        if old and (datetime.fromisoformat(new["sourceGenerated"].replace("Z","+00:00"))<datetime.fromisoformat(old["sourceGenerated"].replace("Z","+00:00")) or new["plants"]<old["plants"]*.9):
            raise ValueError("source regression")
        new["refreshStatus"]="ok"
    except Exception as e:
        print("Shared Energy refresh unavailable:",type(e).__name__)
        if not old:return {}
        new={**old,"refreshStatus":"retained"}
    new["lastAttempt"]=now.isoformat(timespec="seconds")
    tmp=path.with_suffix(".tmp")
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    tmp.replace(path)
    return new
if __name__=="__main__":build()
