"""Single bounded ENTSO-E open-data collector; no prices or actual generation.
Only forecast load (6.1.b) and physical flows (12.1.g), selected Nordic areas.
No secret URLs, raw responses, or unlicensed datasets in public output.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PATH = "data/entsoe-open.json"
API = "https://web-api.tp.entsoe.eu/api"
SOURCE = "ENTSO-E Transparency Platform"
TERMS = "https://transparencyplatform.zendesk.com/hc/en-us/articles/40921911218961-Legal-Terms-and-Conditions"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ZONES = {"NO1":"10YNO-1--------2","NO2":"10YNO-2--------T",
         "NO3":"10YNO-3--------J","NO4":"10YNO-4--------9","NO5":"10Y1001A1001A48H",
         "SE1":"10Y1001A1001A44P","SE2":"10Y1001A1001A45N","SE3":"10Y1001A1001A46L",
         "SE4":"10Y1001A1001A47J","DK1":"10YDK-1--------W","DK2":"10YDK-2--------M",
         "FI":"10YFI-1--------U","DE-LU":"10Y1001A1001A82H",
         "FR":"10YFR-RTE------C","NL":"10YNL----------L"}
BORDERS = (("NO1","SE3"),("NO4","SE1"),("NO2","DK1"))
RES = {"PT15M":15,"PT30M":30,"PT60M":60,"PT1H":60}
MAX_XML = 2_000_000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def stamp(t):
    return t.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def parse_time(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.utcoffset()!=timedelta(0) or t.second or t.microsecond:
        raise ValueError("utc_required")
    return t

def read(params, token, start, end):
    if not token or end-start!=timedelta(days=1):
        raise ValueError("invalid_request")
    query={**params,"securityToken":token,"periodStart":start.strftime("%Y%m%d%H%M"),"periodEnd":end.strftime("%Y%m%d%H%M")}
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(query),
             headers={"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev)","Accept":"application/xml"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(req,timeout=15) as response:
        raw=response.read(MAX_XML+1)
    if len(raw)>MAX_XML:
        raise ValueError("size")
    return raw

def parse(raw, params, start, end):
    if len(raw)>MAX_XML or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("xml_guard")
    root=ET.fromstring(raw)
    for el in root.iter():
        el.tag=el.tag.rsplit("}",1)[-1]
    forecast=params["documentType"]=="A65"
    expected_root="GL_MarketDocument" if forecast else "Publication_MarketDocument"
    if root.tag!=expected_root or root.findtext("type")!=params["documentType"]:
        raise ValueError("document_type")
    if forecast and root.findtext("process.processType")!="A01":
        raise ValueError("not_day_ahead")
    rows={}
    series=root.findall("TimeSeries")
    if not series or len(series)>30:
        raise ValueError("series")
    for ts in series:
        if forecast:
            if ts.findtext("outBiddingZone_Domain.mRID")!=params["outBiddingZone_Domain"]:
                raise ValueError("wrong_area")
        else:
            if any(ts.findtext(k+".mRID")!=params[k.replace(".","_")] for k in ("in_Domain","out_Domain")):
                raise ValueError("wrong_direction")
        if ts.findtext("quantity_Measure_Unit.name")!="MAW":
            raise ValueError("not_mw")
        curve=ts.findtext("curveType")
        if curve not in ("A01","A03") or ts.find("cancelledTS") is not None:
            raise ValueError("unsupported_curve")
        for p in ts.findall("Period"):
            a=parse_time(p.findtext("timeInterval/start") or "")
            b=parse_time(p.findtext("timeInterval/end") or "")
            minutes=RES.get(p.findtext("resolution"))
            if not minutes or not a<b or b-a>timedelta(days=2):
                raise ValueError("period")
            step=timedelta(minutes=minutes)
            if (b-a)%step:
                raise ValueError("period_alignment")
            count=(b-a)//step
            values={}
            for point in p.findall("Point"):
                i=int(point.findtext("position") or "")
                if i<1 or i>count or i in values:
                    raise ValueError("position")
                value=Decimal(point.findtext("quantity") or "")
                if not value.is_finite() or abs(value)>Decimal("1000000") or forecast and value<0:
                    raise ValueError("quantity")
                values[i]=value
            # Preserve only explicit reported blocks: A03 missing points are
            # not automatically expanded until missing-block semantics validated.
            # For A01 each reported point is one interval, gaps remain gaps.
            for i,v in values.items():
                t=a+(i-1)*step
                if not start<=t<end:
                    continue
                key=stamp(t)
                if key in rows:
                    raise ValueError("overlap")
                rows[key]={"startUtc":key,"resolutionMinutes":minutes,
                           "mw":float(v),"curveType":curve}
    if not rows or len(rows)>96:
        raise ValueError("no_or_excess_points")
    return [rows[k] for k in sorted(rows)]

def plan():
    for zone,eic in ZONES.items():
        yield {"id":"load-forecast:"+zone,"kind":"day_ahead_load_forecast","zone":zone,
               "article":"6.1.b"}, {"documentType":"A65","processType":"A01","outBiddingZone_Domain":eic}
    for a,b in BORDERS:
        for source,dest in ((a,b),(b,a)):
            yield {"id":"flow:"+source+":"+dest,"kind":"physical_flow","from":source,"to":dest,
                   "article":"12.1.g"},{"documentType":"A11","out_Domain":ZONES[source],"in_Domain":ZONES[dest]}

def collect(token, now=None, reader=read):
    now=now or datetime.now(timezone.utc)
    end=now.replace(hour=0,minute=0,second=0,microsecond=0)
    start=end-timedelta(days=1)
    rows=[]
    blocked=False
    for meta,params in plan():
        row={**meta,"startUtc":stamp(start),"endUtc":stamp(end),"unit":"MW"}
        if not token:
            row["status"]="awaiting_token"
        elif blocked:
            row["status"]="skipped_provider_limit"
        else:
            try:
                row["points"]=parse(reader(params,token,start,end),params,start,end)
                row["status"]="ok"
            except urllib.error.HTTPError as e:
                row.update(status="unavailable",httpStatus=int(e.code))
                if e.code in (401,403,429):
                    blocked=True
            except (ValueError,InvalidOperation,ET.ParseError,OSError):
                row["status"]="unavailable"
            except Exception:
                row["status"]="unavailable"
        rows.append(row)
    return {"schemaVersion":1,"generated":stamp(now),"source":SOURCE,
            "sourceUrl":"https://transparency.entsoe.eu/","license":"CC BY 4.0",
            "licenseUrl":LICENSE,"termsUrl":TERMS,"reuseListDate":"2023-10-18",
            "changes":"Selected Nordic/European areas, normalized UTC and MW, explicit reported points only; A03 not expanded. Not actual load, prices or complete interval coverage.",
            "series":rows}

def build(root=ROOT):
    doc=collect(os.getenv("STOCKWATCH_ENTSOE_TOKEN","").strip())
    path=root/PATH
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    catalog=root/"data/dataset-catalog.json"
    d=json.loads(catalog.read_text(encoding="utf-8"))
    count=sum(len(s.get("points",[])) for s in doc["series"])
    d["datasets"]=[x for x in d["datasets"] if x.get("path")!=PATH]+[
        {"name":"ENTSO-E open energy reference series","path":PATH,"records":count,
         "license":"CC BY 4.0; selected load forecasts and physical flows; ENTSO-E Transparency Platform"}]
    catalog.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("ENTSO-E open: successful series",sum(s["status"]=="ok" for s in doc["series"]),
          "of",len(doc["series"]),"explicit points",count)
    return doc

if __name__=="__main__":
    build()
