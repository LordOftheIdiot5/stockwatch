"""Report actual retained historical coverage, not theoretical feed availability."""
from pathlib import Path
from datetime import datetime, timezone,date
import json,math
ROOT=Path(__file__).resolve().parents[1]
OUT="data/history-coverage.json"
def load(p):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}
def validday(x):
    try:
        v=date.fromisoformat(x)
        return v<=datetime.now(timezone.utc).date() and len(x)==10
    except (TypeError,ValueError):return False
def summary(dates):
    return {"observations":len(dates),"first":min(dates,default=None),"last":max(dates,default=None)}
def num(v):return type(v) in (float,int) and math.isfinite(v) and v>0
def build(root=ROOT):
    data=root/"data"
    histories=[];seen=[]
    for f in sorted((data/"history").glob("*.json")):
        d=load(f)
        if not (d.get("redistributionPermitted") is True and d.get("licenseReference") and d.get("sourceUrl") and d.get("source") and d.get("ticker")==f.stem and d.get("currency") and type(d.get("adjusted")) is bool):continue
        dates=sorted({x["date"] for x in d.get("bars",[]) if isinstance(x,dict) and validday(x.get("date")) and num(x.get("close"))})
        if not dates:continue
        histories.append({"ticker":d["ticker"],"source":d["source"],"sourceUrl":d["sourceUrl"],"licenseReference":d["licenseReference"],"currency":d["currency"],"adjusted":d["adjusted"],**summary(dates)})
        seen.extend(dates)
    reference_histories=[];reference_dates=[]
    for f in sorted((data/"licensed-reference-history").glob("*.json")):
        d=load(f)
        if not (d.get("redistributionPermitted") is True and d.get("priceType")=="end_of_day" and d.get("listingId") and d.get("licenseReference") and d.get("sourceUrl") and d.get("source") and d.get("currency") and type(d.get("adjusted")) is bool):continue
        dates=sorted({x["date"] for x in d.get("bars",[]) if isinstance(x,dict) and validday(x.get("date")) and num(x.get("close"))})
        if dates:
            reference_histories.append({"listingId":d["listingId"],"source":d["source"],"currency":d["currency"],**summary(dates)})
            reference_dates.extend(dates)
    spreads=load(data/"spread-observations.json")
    ratios=[];pairs=0
    for key,points in spreads.get("pairs",{}).items():
        dates={x["date"] for x in points if isinstance(x,dict) and validday(x.get("date")) and num(x.get("value"))}
        if dates:pairs+=1;ratios.extend(dates)
    news=load(data/"news-store/index.json");months=news.get("months",[])
    first=[x["first"] for x in months if isinstance(x.get("first"),str) and x.get("count",0)>0]
    last=[x["last"] for x in months if isinstance(x.get("last"),str) and x.get("count",0)>0]
    mapping=load(data/"research-coverage.json").get("records",[])
    directory=load(data/"instrument-directory.json").get("records",[])
    audit={"generated":datetime.now(timezone.utc).isoformat(),"licensedEquityHistory":{"series":len(histories),**summary(seen),"details":histories},"licensedReferenceHistory":{"series":len(reference_histories),**summary(reference_dates),"details":reference_histories},"dailyABIndicators":{"series":pairs,**summary(ratios),"notice":"One observed ratio per UTC scan day, not reconstructed OHLCV; commercial rights need review."},"newsMetadata":{"records":news.get("total",0),"first":min(first,default=None),"last":max(last,default=None),"notice":"Source-linked metadata, not full publisher articles."},"instrumentReference":{"venueRecords":len(directory),"researchTargets":len(mapping),"currentCandidates":sum(r.get("mappingStatus")=="candidate" for r in mapping),"observedMappingChanges":sum(len(r.get("mappingHistory",[])) for r in mapping)}}
    (root/OUT).write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return audit
if __name__=="__main__":print(json.dumps(build(),ensure_ascii=False))
