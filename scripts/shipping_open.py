"""Import source-attributed USDA bulk grain ocean transportation cost indices.

These are weekly index points, base year 2017=100, NOT commercial voyage
quotes or freight rates. USD/tonne baseline values describe the *index
construction*, not a conversion permission or published route rate.
"""
from __future__ import annotations
import json,math,re,urllib.parse,urllib.request,urllib.error,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT="data/shipping-open.json"
USDA_ID="8uye-ieij"
SOURCE="https://agtransport.usda.gov/Transportation-Costs/Grain-Transportation-Cost-Indicators/8uye-ieij"
API="https://agtransport.usda.gov/resource/"+USDA_ID+".json"
USER_AGENT="StockwatchResearch/1.0 (+https://stocks.nordl.dev)"
ROUTES={
    "usda:gulf-japan-index":{"field":"gulf_vessel","name":"US Gulf → Japan ocean grain freight cost index","route":"US Gulf → Japan","baseUsdPerTonne":39.33},
    "usda:pnw-japan-index":{"field":"pacific_vessel","name":"Pacific Northwest → Japan ocean grain freight cost index","route":"Pacific Northwest → Japan","baseUsdPerTonne":21.05}
}
RELATED=[
 {"name":"USDA Bulk Grain Ocean Freight Rates","url":"https://agtransport.usda.gov/Bulk/Bulk-Grain-Ocean-Freight-Rates/ehic-wtxb",
  "status":"link_only","reason":"Third-party O'Neil Commodity Consulting attribution; no raw commercial freight rate is copied."},
 {"name":"IMF PortWatch","url":"https://portwatch.imf.org/","status":"link_only",
  "reason":"Maritime port/chokepoint activity; not freight rate quotations. Dataset/API terms require separate review."},
 {"name":"UNCTADstat Maritime Transport","url":"https://unctadstat.unctad.org/","status":"link_only",
  "reason":"Maritime connectivity and trade statistics; not voyage freight rates."},
 {"name":"Baltic Exchange","url":"https://www.balticexchange.com/en/data-services/Methodology/market-data.html","status":"license_required",
  "reason":"Capesize, Panamax, tanker and Newcastle route rates require licensed market data and web display rights."},
 {"name":"Freightos FBX","url":"https://apidocs.freightos.com/reference/get_fbx-data","status":"license_required",
  "reason":"Container trade-lane rate indices; API credentials and permitted display rights required."}
]
def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def valid_rows(rows):
    """Only accept documented USDA columns, real dates, finite positive indices."""
    if not isinstance(rows,list):raise ValueError("invalid_usda_payload")
    parsed={key:{} for key in ROUTES}
    for row in rows:
        if not isinstance(row,dict):continue
        date=str(row.get("date") or "")[:10]
        if not re.fullmatch(r"20\d\d-\d\d-\d\d",date):continue
        try:datetime.strptime(date,"%Y-%m-%d")
        except ValueError:continue
        for key,description in ROUTES.items():
            try:
                n=float(row.get(description["field"]))
                if not math.isfinite(n) or n<=0 or n>10000:continue
                parsed[key][date]=round(n,4)
            except (ValueError,TypeError):pass
    return {key:[{"date":d,"value":v} for d,v in sorted(values.items())[-170:]]
            for key,values in parsed.items()}

def fetch_rows(limit=170):
    args=urllib.parse.urlencode({"$select":"date,gulf_vessel,pacific_vessel",
              "$order":"date DESC","$limit":min(300,max(1,limit))})
    req=urllib.request.Request(API+"?"+args,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=32) as response:
                raw=response.read(1000001)
                if len(raw)>1000000:raise ValueError("usda_response_too_large")
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            if attempt or e.code not in (429,502,503,504):raise
        except (TimeoutError,urllib.error.URLError):
            if attempt:raise
        time.sleep(2)
    raise RuntimeError("unreachable")

def build(root=ROOT):
    path=root/OUT
    try:previous=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):previous={}
    series=[]
    status={"status":"not_checked","sourceUrl":SOURCE,"lastSuccessAt":None}
    try:
        parsed=valid_rows(fetch_rows())
        for key,meta in ROUTES.items():
            values=parsed[key]
            if not values:continue
            series.append({"key":key,"label":meta["name"],"route":meta["route"],
                "provider":"USDA Agricultural Marketing Service","category":"Ocean grain cost index",
                "unit":"index, 2017 = 100","baseYear":2017,"indexBaseUsdPerTonne":meta["baseUsdPerTonne"],
                "frequency":"weekly","sourceUrl":SOURCE,"license":"USDA/AMS aggregated non-confidential, non-copyrighted source; attribution given; check underlying source notes",
                "period":values[-1]["date"],"value":values[-1]["value"],
                "history":values,"observedAt":timestamp(),"isActualRate":False,
                "isBalticBenchmark":False})
        if len(series)!=len(ROUTES):raise ValueError("usda_ocean_indices_missing")
        status={"status":"ok","sourceUrl":SOURCE,"records":len(series),
                "observations":sum(len(s["history"]) for s in series),"lastSuccessAt":timestamp()}
    except Exception as error:
        series=previous.get("series") or []
        prior=previous.get("source") or {}
        status={"status":"error","sourceUrl":SOURCE,"errorType":type(error).__name__,
                "lastSuccessAt":prior.get("lastSuccessAt"),"records":len(series),
                "note":"Previous observations preserved with original timestamps; not refreshed."}
        if isinstance(error,urllib.error.HTTPError):status["httpStatus"]=int(error.code)
    output={"generated":timestamp(),"notice":"USDA weekly ocean grain cost indices (2017=100), NOT spot freight quotes, not USD/tonne rates, not Baltic Exchange route assessments.",
            "source":status,"series":series,"relatedSources":RELATED}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    catalog_path=root/"data/dataset-catalog.json"
    if catalog_path.exists():
        try:
            catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
            old=catalog.get("datasets") or []
            entry={"name":"USDA weekly ocean-grain freight cost indices","path":OUT,
                   "records":sum(len(s.get("history") or []) for s in series),
                   "license":"USDA AMS source-attributed index observations; not commercial freight quotes"}
            catalog["datasets"]=[x for x in old if x.get("path")!=OUT]+[entry]
            catalog["generated"]=timestamp()
            catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        except (OSError,ValueError,TypeError):pass
    print("USDA shipping indices: "+status["status"]+"; series="+str(len(series)))
    return output

if __name__=="__main__":build()
