"""Import provider-authorized daily closes for the expanded reference universe.

Input CSV: listing_id,date,close,volume. Manifest is a locally reviewed grant
and exact provider-to-listing mapping, not an automatic licence determination.
Never put feed credentials or original vendor files inside the public repository.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re
from datetime import date,datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT="data/licensed-price-coverage.json"
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(".tmp")
    temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");temp.replace(p)
def key(id):return hashlib.sha256(id.encode()).hexdigest()[:32]
def allowed(root):
    targets=read(root/"data/research-targets.json")["targets"]
    extra=read(root/"data/research-expansion.json")["records"]
    return {"ref:"+x["id"]:x["mic"] for x in targets}|{"registry:"+x["mic"]+":"+x["figi"]:x["mic"] for x in extra}
def validate_grant(m):
    for k in ("publicDisplay","historicalStorage","derivedAnalytics","identityReviewed"):
        if m.get(k) is not True:raise ValueError("Explicit reviewed permission required: "+k)
    # A licensed public EOD chart does not necessarily grant raw trade/file redistribution.
    # Require the raw right to be explicit, but never elevate it to a publication prerequisite.
    if type(m.get("publicRawRedistribution")) is not bool:
        raise ValueError("Explicit reviewed permission required: publicRawRedistribution (true or false)")
    for k in ("provider","sourceUrl","licenseReference"):
        if not isinstance(m.get(k),str) or not m[k].strip():raise ValueError("Missing "+k)
    for k in ("sourceUrl","licenseReference"):
        if not m[k].startswith("https://"):raise ValueError("HTTPS references required")
    if m.get("priceType")!="end_of_day":raise ValueError("Only EOD prices accepted")
    if not isinstance(m.get("listings"),dict) or not m["listings"]:raise ValueError("Exact listing mapping required")
def import_batch(root,csv_path,manifest_path):
    m=read(Path(manifest_path));validate_grant(m);universe=allowed(root)
    grouped={}
    for id,info in m["listings"].items():
        if id not in universe or info.get("mic")!=universe[id] or not info.get("providerSymbol") or not re.fullmatch("[A-Z]{3}",info.get("currency","")) or type(info.get("adjusted")) is not bool:
            raise ValueError("Unreviewed or invalid listing mapping: "+id)
    with Path(csv_path).open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            id=row["listing_id"]
            if id not in m["listings"]:raise ValueError("Unexpected listing")
            d=date.fromisoformat(row["date"]);v=float(row["close"])
            if d>datetime.now(timezone.utc).date() or not math.isfinite(v) or v<=0:raise ValueError("Invalid close/date")
            vol=row.get("volume","").strip();vol=int(vol) if vol else None
            if vol is not None and vol<0:raise ValueError("Negative volume")
            bars=grouped.setdefault(id,{})
            if str(d) in bars:raise ValueError("Duplicate observation")
            bars[str(d)]={"date":str(d),"close":round(v,8),"volume":vol}
    if not grouped:raise ValueError("Empty feed")
    prepared=[]
    index=root/OUT
    existing=read(index) if index.exists() else {"records":[]}
    records={r["listingId"]:r for r in existing["records"]}
    now=datetime.now(timezone.utc).isoformat()
    for id,bars in grouped.items():
        info=m["listings"][id];rel="data/licensed-reference-history/"+key(id)+".json";dest=root/rel
        fixed={"listingId":id,"mic":info["mic"],"providerSymbol":info["providerSymbol"],"currency":info["currency"],"adjusted":info["adjusted"],"source":m["provider"],"sourceUrl":m["sourceUrl"],"licenseReference":m["licenseReference"],"publicDisplayPermitted":True,"rawRedistributionPermitted":m["publicRawRedistribution"],"redistributionPermitted":m["publicRawRedistribution"],"priceType":"end_of_day"}
        if dest.exists():
            prior=read(dest)
            if any(prior.get(k)!=v for k,v in fixed.items()):raise ValueError("Identity or licence changed; review before merging")
            for bar in prior["bars"]:
                if bar["date"] in bars and bar!=bars[bar["date"]]:raise ValueError("Conflicting historical observation")
                bars.setdefault(bar["date"],bar)
        series=[bars[d] for d in sorted(bars)]
        if len(series)<2:raise ValueError("Need two dated closes for initial import")
        last,prev=series[-1],series[-2]
        records[id]={**fixed,"lastDate":last["date"],"previousDate":prev["date"],"close":last["close"],"changePct":round(100*(last["close"]/prev["close"]-1),6),"observations":len(series),"firstDate":series[0]["date"],"historyPath":rel,"importedAt":now}
        prepared.append((dest,{**fixed,"updated":now,"bars":series}))
    # All input conflicts are checked before any write.
    for p,d in prepared:write(p,d)
    result={"generated":now,"notice":"Licensed public-display EOD observations, not live quotes or a right to redistribute raw vendor data; adjacent recorded closes may span non-trading days or gaps. Not included in legacy scanner breadth.", "records":sorted(records.values(),key=lambda r:r["listingId"])}
    write(index,result)
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("csv");p.add_argument("manifest");a=p.parse_args()
    d=import_batch(ROOT,a.csv,a.manifest);print("Licensed reference histories:",len(d["records"]))
