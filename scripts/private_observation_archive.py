"""Private source-aware archive of dated observations (never a Pages output).

Eurostat data is archived with attribution. Scanner quotes are separately
permission-gated, because retaining a copy does not grant market-data rights.
No quote records are created from sparks or synthetic dates.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from private_r2_archive import BUCKET, configuration, immutable_put

ROOT=Path(__file__).resolve().parents[1]

def dated(d):
    try:
        return isinstance(d,str) and date.fromisoformat(d).isoformat()==d
    except (TypeError,ValueError):
        return False

def positive(v):
    return type(v) in (int,float) and math.isfinite(v) and v>0

def payload(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf8")

def scanner_observations(snapshot):
    stamp=snapshot.get("generated")
    try:
        parsed=datetime.fromisoformat(stamp)
        if parsed.tzinfo is None:
            raise ValueError("Missing timestamp offset")
        today=parsed.astimezone(timezone.utc).date().isoformat()
    except (TypeError,ValueError):
        raise ValueError("Invalid scanner snapshot timestamp") from None
    rows=[]
    seen=set()
    for r in snapshot.get("companies",[]):
        if not isinstance(r,dict) or r.get("unavailable") or r.get("priceStatus")!="reported" or not dated(r.get("date")) or r["date"]>today or not positive(r.get("close")):
            continue
        if not all(isinstance(r.get(k),str) and r[k] for k in ("ticker","currency","exchange","name")):
            continue
        if r.get("priceObservedAt")!=stamp:
            continue
        key=(r["exchange"],r["ticker"],r["currency"],r["date"])
        if key in seen:
            raise ValueError("Duplicate listing observation")
        seen.add(key)
        row={k:r[k] for k in ("ticker","name","exchange","currency","date","close")}
        row.update({"firstObservedAt":stamp,"source":"Existing Stockwatch scanner; upstream market data; not certified EOD","officialClose":False})
        if isinstance(r.get("isin"),str) and r["isin"]:
            row["isin"]=r["isin"]
        if isinstance(r.get("mic"),str) and r["mic"]:
            row["mic"]=r["mic"]
        rows.append(row)
    return sorted(rows,key=lambda r:(r["exchange"],r["ticker"],r["currency"],r["date"]))

# Explicit source/series allowlist. Never archive arbitrary mixed-provider files.
OFFICIAL_FILES = {
    "usda-grain-indices":"shipping-open.json",
    "worldbank-port-traffic":"shipping-ports.json",
    "unctad-connectivity":"shipping-connectivity.json",
    "official-energy-macro":"economic-feeds.json",
    "official-fx-macro":"open-data.json",
    "entsoe-open":"entsoe-open.json",
}
def host_is(url,host):
    try:
        u=urlparse(url)
        return u.scheme=="https" and u.hostname==host and not u.username and not u.password
    except (TypeError,ValueError):
        return False

def eligible_series(kind,r):
    if not isinstance(r,dict):
        return False
    key=r.get("key","")
    if not isinstance(key,str):
        return False
    url=r.get("sourceUrl")
    if not isinstance(r.get("license"),str) or not r["license"] or not isinstance(r.get("unit"),str):
        return False
    if kind=="usda-grain-indices":
        return key in ("usda:gulf-japan-index","usda:pnw-japan-index") and host_is(url,"agtransport.usda.gov") and r["unit"]=="index, 2017 = 100"
    if kind=="worldbank-port-traffic":
        return key.startswith("worldbank:container-port-teu:") and host_is(url,"data.worldbank.org") and r["unit"]=="TEU" and "CC BY 4.0" in r["license"]
    if kind=="unctad-connectivity":
        return key.startswith("unctad:lsci-monthly:") and host_is(url,"unctadstat.unctad.org") and "CC BY 3.0 IGO" in r["license"]
    if kind=="official-energy-macro":
        return (key in ("eia:RBRTE","eia:RWTC") and host_is(url,"www.eia.gov") and r.get("provider")=="eia") or (key=="fred:PCU483111483111" and host_is(url,"fred.stlouisfed.org") and "public domain" in r["license"])
    if kind=="official-fx-macro":
        return (key in ("fx:EUR/NOK","fx:USD/NOK") and host_is(url,"data.norges-bank.no") and r["license"]=="NLOD 2.0") or (key=="fx:EUR/USD" and host_is(url,"data-api.ecb.europa.eu") and r.get("provider")=="ecb") or (key.startswith("hicp_yoy:") and host_is(url,"ec.europa.eu") and r.get("provider")=="eurostat") or (key.split(":")[0] in ("NE.EXP.GNFS.ZS","NY.GDP.MKTP.KD.ZG") and host_is(url,"api.worldbank.org") and "CC BY 4.0" in r["license"])
    return False

def official_snapshot(kind,data):
    if not isinstance(data,dict) or not isinstance(data.get("series"),list):
        raise ValueError("Invalid official data envelope")
    if kind=="entsoe-open":
        if data.get("license")!="CC BY 4.0" or not host_is(data.get("sourceUrl"),"transparency.entsoe.eu"):
            raise ValueError("Unexpected ENTSO-E license")
        rows=[r for r in data["series"] if isinstance(r,dict) and (r.get("kind"),r.get("article")) in {("day_ahead_load_forecast","6.1.b"),("physical_flow","12.1.g")} and r.get("unit")=="MW" and r.get("points")]
        # Retain the published metadata and eligible series only.
        meta={k:data[k] for k in ("schemaVersion","generated","source","sourceUrl","license","licenseUrl","termsUrl","reuseListDate","changes") if k in data}
    else:
        rows=[r for r in data["series"] if eligible_series(kind,r) and isinstance(r.get("history"),list) and r["history"]]
        meta={k:data[k] for k in ("generated","notice") if k in data}
    if not rows:
        raise ValueError("No eligible observations")
    return {**meta,"archiveDataset":kind,"series":rows}

def archive_dataset(client,kind,obj,day):
    if not dated(day) or kind not in {"eurostat-roro","scanner-observations",*OFFICIAL_FILES}:
        raise ValueError("Invalid archive partition")
    raw=payload(obj)
    digest=hashlib.sha256(raw).hexdigest()
    key=f"observations/{kind}/{day}/{digest}.json"
    status=immutable_put(client,raw,key,{"type":kind,"publicpublication":"false"},"application/json")
    return {"dataset":kind,"day":day,"storageStatus":status,"publicPublication":False}

def collect(client,env,root=ROOT,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day=now.date().isoformat()
    statuses=[]
    official=json.loads((root/"data/shipping-roro-traffic.json").read_text(encoding="utf8"))
    if official.get("schemaVersion")!=1 or official.get("provider")!="Eurostat" or official.get("datasetCode")!="mar_go_qmc" or not official.get("licenseUrl") or not official.get("series"):
        raise ValueError("Unrecognized official dataset")
    statuses.append(archive_dataset(client,"eurostat-roro",official,day))
    for kind,filename in OFFICIAL_FILES.items():
        try:
            data=json.loads((root/"data"/filename).read_text(encoding="utf8"))
            obj=official_snapshot(kind,data)
            result=archive_dataset(client,kind,obj,day)
            result["series"]=len(obj["series"])
            result["observations"]=sum(len(r.get("history",r.get("points",[]))) for r in obj["series"])
            statuses.append(result)
        except Exception as exc:
            statuses.append({"dataset":kind,"storageStatus":"failed","errorType":type(exc).__name__,"publicPublication":False})
    if env.get("STOCKWATCH_SCANNER_RETENTION_APPROVED")!="true":
        statuses.append({"dataset":"scanner-observations","storageStatus":"permission_pending","publicPublication":False})
        return statuses
    snapshot=json.loads((root/"data/signals.json").read_text(encoding="utf8"))
    rows=scanner_observations(snapshot)
    if not rows:
        statuses.append({"dataset":"scanner-observations","storageStatus":"no_valid_observations","publicPublication":False})
        return statuses
    # Partition by original market observation date, not collection date.
    for observed in sorted({r["date"] for r in rows}):
        obj={"schemaVersion":1,"collectedAt":snapshot["generated"],"observationDate":observed,"notice":"Private retention only; not licensed for public distribution or verified official closes.","records":[r for r in rows if r["date"]==observed]}
        statuses.append(archive_dataset(client,"scanner-observations",obj,observed))
    return statuses

def main():
    try:
        account=configuration(os.environ,smoke_only=True)
        import boto3
        from botocore.config import Config
        client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3,"mode":"standard"}))
        rows=collect(client,os.environ)
        for row in rows:
            print(json.dumps(row))
        return 1 if any(r["storageStatus"]=="failed" for r in rows) else 0
    except Exception as exc:
        print(json.dumps({"status":"failed","errorType":type(exc).__name__,"publicPublication":False}))
        return 1

if __name__=="__main__":
    sys.exit(main())
