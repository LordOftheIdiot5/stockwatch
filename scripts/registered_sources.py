"""Optional credential-backed official-data connectors.

Keys must come from GitHub Actions secrets. Never publish tokens, request URLs
containing tokens, or paid/personal-use feed records. OpenFIGI results remain
candidate instruments; ENTSO-E electricity prices are probe-only until a
dataset-specific public reuse decision is recorded.
"""
from __future__ import annotations
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/registered-source-status.json"
UA="StockwatchResearch/1.0 (+https://stocks.nordl.dev)"
FIGI_URL="https://api.openfigi.com/v3/mapping"
ENTSOE_URL="https://web-api.tp.entsoe.eu/api"
# Validated market identification codes; never use an unqualified symbol
# for a confident match. Other exchanges remain unmapped candidates.
MICS={"OL":"XOSL","ST":"XSTO","CO":"XCSE","HE":"XHEL",
      "PA":"XPAR","AS":"XAMS","DE":"XETR","BR":"XBRU"}
NO2_DOMAIN="10YNO-2--------T"

def current_time():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def _read(req, cap=1500000):
    with urllib.request.urlopen(req,timeout=20) as resp:
        payload=resp.read(cap+1)
        if len(payload)>cap:
            raise ValueError("response_too_large")
        return payload

def figi_jobs(directory, limit=100):
    jobs=[]
    for row in directory.get("entities") or []:
        ticker=str(row.get("ticker") or "")
        if "." not in ticker:
            continue
        name,suffix=ticker.rsplit(".",1)
        mic=MICS.get(suffix)
        if not mic or not re.fullmatch(r"[A-Z0-9-]{1,18}",name):
            continue
        known_isin=str(row.get("isin") or "").upper()
        if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}",known_isin):
            jobs.append((ticker,{"idType":"ID_ISIN","idValue":known_isin,"micCode":mic}))
        else:
            jobs.append((ticker,{"idType":"TICKER","idValue":name,"micCode":mic}))
        if len(jobs)>=limit:
            break
    return jobs

def parse_figi(payload,jobs):
    if not isinstance(payload,list) or len(payload)!=len(jobs):
        raise ValueError("invalid_openfigi_results")
    candidates=[]
    ambiguous=0
    for (watch_ticker,job),record in zip(jobs,payload):
        data=record.get("data") or []
        # Never silently join ambiguous instruments to a watchlist company.
        if not isinstance(data,list) or not data:
            continue
        matches=[x for x in data if isinstance(x,dict) and
                 str(x.get("marketSector") or "").lower()=="equity" and
                 re.fullmatch(r"BBG[A-Z0-9]{9}",str(x.get("figi") or "")) and
                 ((job["idType"]=="ID_ISIN") or
                  str(x.get("ticker") or "").upper()==str(job["idValue"]).upper())]
        if len(matches)!=1:
            if matches:
                ambiguous+=1
            continue
        x=matches[0]
        candidates.append({"ticker":watch_ticker,"figi":x["figi"],
             "shareClassFIGI":x.get("shareClassFIGI"),
             "compositeFIGI":x.get("compositeFIGI"),
             "name":x.get("name"),"marketSector":"Equity",
             "match":"single_instrument_same_mic_candidate",
             "verified":False,"sourceUrl":"https://www.openfigi.com/",
             "checkedAt":current_time()})
    return candidates,ambiguous

def openfigi(directory,key):
    jobs=figi_jobs(directory)
    if not jobs:
        return {"count":0,"ambiguous":0,"candidates":[]}
    # Compatible with free authenticated (100 jobs/request) and unauthenticated (10).
    take=100 if key else 10
    all_candidates=[]
    ambiguous=0
    for i in range(0,len(jobs),take):
        chunk=jobs[i:i+take]
        headers={"Content-Type":"application/json","User-Agent":UA}
        if key:
            headers["X-OPENFIGI-APIKEY"]=key
        req=urllib.request.Request(FIGI_URL,
            data=json.dumps([j for _,j in chunk]).encode("utf-8"),
            headers=headers,method="POST")
        results=json.loads(_read(req).decode("utf-8"))
        candidates,amb=parse_figi(results,chunk)
        all_candidates.extend(candidates)
        ambiguous+=amb
    return {"count":len(all_candidates),"ambiguous":ambiguous,
            "candidates":all_candidates}

def inspect_entsoe_xml(raw):
    """Count genuine day-ahead data points without exporting licensed rates."""
    root=ET.fromstring(raw)
    if root.tag.split("}")[-1]!="Publication_MarketDocument":
        raise ValueError("no_price_document")
    points=0
    for element in root.iter():
        if element.tag.split("}")[-1]=="Point":
            value=next((x.text for x in element if x.tag.split("}")[-1]=="price.amount"),None)
            try:
                if value is not None and abs(float(value))<1000000:
                    points+=1
            except (ValueError,TypeError):
                continue
    return points

def entsoe_probe(token):
    end=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    start=end-timedelta(days=1)
    qs={"securityToken":token,"documentType":"A44",
        "in_Domain":NO2_DOMAIN,"out_Domain":NO2_DOMAIN,
        "periodStart":start.strftime("%Y%m%d%H%M"),
        "periodEnd":end.strftime("%Y%m%d%H%M")}
    # URL contains a secret. Never persist it or print exceptions including URL.
    url=ENTSOE_URL+"?"+urllib.parse.urlencode(qs)
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/xml"})
    count=inspect_entsoe_xml(_read(req,cap=4500000))
    if not count:
        raise ValueError("no_valid_price_points")
    return {"seriesAvailable":True,"pointsChecked":count,
            "area":"NO2","periodStart":start.isoformat(),"periodEnd":end.isoformat(),
            "dataStored":False,"publicDisplay":False,
            "license":"Pending verification of applicable ENTSO-E data item and primary-owner rights",
            "sourceUrl":"https://transparency.entsoe.eu/"}

def update_catalog(root, count):
    path=root/"data/dataset-catalog.json"
    try:
        catalog=json.loads(path.read_text(encoding="utf-8"))
    except (ValueError,OSError):
        catalog={"datasets":[]}
    entries=catalog.setdefault("datasets",[])
    if not isinstance(entries,list):
        raise ValueError("invalid_dataset_catalog")
    record={"name":"OpenFIGI instrument identity candidates",
            "path":"data/registered-source-status.json","records":count,
            "license":"OpenFIGI reference symbology only; matches unverified, ENTSO-E observations withheld"}
    catalog["datasets"]=[x for x in entries if x.get("path")!=record["path"]]+[record]
    catalog["generated"]=current_time()
    path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def build(root=ROOT):
    output=root/"data/registered-source-status.json"
    directory=json.loads((root/"data/issuer-identities.json").read_text(encoding="utf-8"))
    figi_key=os.getenv("STOCKWATCH_OPENFIGI_KEY","").strip()
    entsoe_token=os.getenv("STOCKWATCH_ENTSOE_TOKEN","").strip()
    entries={}
    records=[]
    if not figi_key:
        entries["openfigi"]={"status":"awaiting_key",
            "sourceUrl":"https://www.openfigi.com/api/documentation"}
    else:
        try:
            value=openfigi(directory,figi_key)
            records=value["candidates"]
            entries["openfigi"]={"status":"ok","candidateCount":value["count"],
                "ambiguous":value["ambiguous"],
                "verified":0,"sourceUrl":"https://www.openfigi.com/api/documentation"}
        except Exception as exc:
            # Never include URL with API keys, response body, or exception text.
            entries["openfigi"]={"status":"error","errorType":type(exc).__name__,
                "sourceUrl":"https://www.openfigi.com/api/documentation"}
    if not entsoe_token:
        entries["entsoe"]={"status":"awaiting_token",
            "sourceUrl":"https://transparency.entsoe.eu/"}
    else:
        try:
            value=entsoe_probe(entsoe_token)
            entries["entsoe"]={"status":"probe_ok",**value}
        except Exception as exc:
            entries["entsoe"]={"status":"error","errorType":type(exc).__name__,
                "sourceUrl":"https://transparency.entsoe.eu/"}
    result={"generated":current_time(),
            "notice":"OpenFIGI matches are instrument candidates, not verified issuer identities. ENTSO-E raw rates not published.",
            "sources":entries,"figiCandidates":records[:150]}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    update_catalog(root,len(records))
    print("Registered sources: "+", ".join(k+"="+v["status"] for k,v in entries.items()))
    return result

if __name__=="__main__":
    build()
