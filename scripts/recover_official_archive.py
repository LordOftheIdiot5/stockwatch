"""Restore missing eligible official series from private immutable R2 snapshots.

Never use this path for private equity prices, news or benchmark quotes.
Existing nonempty source series win; no newer-date or currency substitution.
Archived observations keep their source timestamps. No public archive endpoint.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from private_observation_archive import OFFICIAL_FILES, official_snapshot, host_is, ROOT
from private_r2_archive import BUCKET, configuration
from collect_roro_traffic import COUNTRIES, period_valid, number_valid

FILES={"eurostat-roro":"shipping-roro-traffic.json",**OFFICIAL_FILES}
MAX_BYTES=24*1024*1024
MAX_OBJECTS=100
def valid_roro(d):
    if not isinstance(d,dict) or d.get("schemaVersion")!=1 or d.get("provider")!="Eurostat" or d.get("datasetCode")!="mar_go_qmc" or not host_is(d.get("sourceUrl"),"ec.europa.eu") or not host_is(d.get("licenseUrl"),"ec.europa.eu"):
        raise ValueError("Unexpected Eurostat source")
    rows=[]
    for r in d.get("series",[]):
        if not isinstance(r,dict) or r.get("countryCode") not in COUNTRIES or r.get("key")!="eurostat:mar_go_qmc:RO_TOT:"+r["countryCode"] or r.get("unit")!="thousand tonnes" or r.get("frequency")!="quarterly":
            continue
        h=r.get("history")
        if isinstance(h,list) and h and all(isinstance(p,dict) and period_valid(p.get("period")) and number_valid(p.get("value")) for p in h) and r.get("period")==h[-1]["period"] and r.get("value")==h[-1]["value"]:
            rows.append(r)
    if not rows:
        raise ValueError("No eligible Eurostat series")
    return {**{k:d[k] for k in ("schemaVersion","observedOn","sourceUpdated","provider","datasetCode","sourceUrl","apiUrl","licenseUrl","license","notice") if k in d},"series":rows}

def validate(kind,data):
    return valid_roro(data) if kind=="eurostat-roro" else official_snapshot(kind,data)

def latest_snapshot(client,kind,now):
    if kind not in FILES:
        raise ValueError("Non-eligible dataset")
    # Search newest day first, bounded to a seven-day recovery window.
    for days in range(7):
        day=(now.date()-timedelta(days=days)).isoformat()
        prefix=f"observations/{kind}/{day}/"
        items=[]
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix,PaginationConfig={"MaxItems":MAX_OBJECTS}):
            items.extend(x for x in page.get("Contents",[]) if re.fullmatch(re.escape(prefix)+r"[a-f0-9]{64}\.json",x.get("Key","")) and 0<x.get("Size",0)<=MAX_BYTES)
        for item in sorted(items,key=lambda x:(x["LastModified"],x["Key"]),reverse=True):
            try:
                obj=client.get_object(Bucket=BUCKET,Key=item["Key"])
                body=obj["Body"]
                try:
                    raw=body.read(MAX_BYTES+1)
                finally:
                    body.close()
                digest=hashlib.sha256(raw).hexdigest()
                if len(raw)>MAX_BYTES or digest!=item["Key"].rsplit("/",1)[-1][:-5] or obj.get("Metadata",{}).get("sha256")!=digest:
                    continue
                return validate(kind,json.loads(raw)),day
            except (ValueError,TypeError,KeyError,UnicodeError):
                continue
    return None,None

def recover(kind,current,archived,day):
    """Fill only missing/empty series; never replace nonempty series or unrelated metadata."""
    if not isinstance(current,dict) or not isinstance(current.get("series"),list):
        # A partial archive cannot reconstruct mixed-source envelopes.
        if kind in ("official-energy-macro","official-fx-macro","entsoe-open"):
            return current,0
        current={k:v for k,v in archived.items() if k not in ("series","archiveDataset")}
        current["series"]=[]
    key="id" if kind=="entsoe-open" else "key"
    history="points" if kind=="entsoe-open" else "history"
    rows=list(current["series"])
    positions={}
    duplicates=set()
    for i,r in enumerate(rows):
        if not isinstance(r,dict) or not isinstance(r.get(key),str):
            continue
        if r[key] in positions:
            duplicates.add(r[key])
        positions[r[key]]=i
    added=0
    for r in archived["series"]:
        identifier=r.get(key)
        if not isinstance(identifier,str) or identifier in duplicates:
            continue
        i=positions.get(identifier)
        if i is not None:
            prior=rows[i]
            # Do not change identities, units, dates or nonempty data.
            if prior.get(history) or prior.get("unit") not in (None,r.get("unit")):
                continue
            fields=("kind","article","zone") if kind=="entsoe-open" else ("provider","sourceUrl","countryCode","frequency")
            if any(prior.get(k) is not None and prior[k]!=r.get(k) for k in fields):
                continue
        restored={**r,"archiveRecovery":{"snapshotDay":day,"status":"retained"}}
        if kind=="entsoe-open":
            restored["status"]="retained"
        if i is None:
            positions[identifier]=len(rows)
            rows.append(restored)
        else:
            rows[i]=restored
        added+=1
    if not added:
        return current,0
    result={**current,"series":rows,"archiveRecovery":{"snapshotDay":day,"restoredSeries":added,"status":"retained"}}
    if kind in ("usda-grain-indices","worldbank-port-traffic","unctad-connectivity"):
        source=current.get("source",{})
        result["source"]={**(source if isinstance(source,dict) else {}),"status":"retained","lastSuccessAt":source.get("lastSuccessAt",archived.get("generated")) if isinstance(source,dict) else archived.get("generated"),"series":len(rows),"observations":sum(len(r.get("history",[])) for r in rows if isinstance(r,dict))}
    return result,added

def run(client,root=ROOT,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    results=[]
    for kind,filename in FILES.items():
        path=root/"data"/filename
        try:
            current=json.loads(path.read_text(encoding="utf8"))
        except (OSError,ValueError):
            current=None
        archived,day=latest_snapshot(client,kind,now)
        if archived is None:
            results.append({"dataset":kind,"restoredSeries":0,"status":"archive_unavailable"})
            continue
        result,count=recover(kind,current,archived,day)
        if count:
            tmp=path.with_suffix(".recovery.tmp")
            tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
            tmp.replace(path)
        results.append({"dataset":kind,"restoredSeries":count,"status":"retained" if count else "unchanged"})
    return results

def main():
    try:
        account=configuration(os.environ,smoke_only=True)
        import boto3
        from botocore.config import Config
        client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3,"mode":"standard"}))
        for result in run(client):
            print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"failed","errorType":type(exc).__name__}))
        return 1

if __name__=="__main__":
    sys.exit(main())
