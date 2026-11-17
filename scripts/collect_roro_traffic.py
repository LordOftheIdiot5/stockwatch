"""Refresh Eurostat Ro-Ro cargo traffic; keep dated observations on source failure.
Run from the repository root: python scripts/collect_roro_traffic.py
No source-side authentication or third-party quote redistribution.
"""
import datetime as dt
import json
import math
import pathlib
import re
import urllib.parse
import urllib.request

COUNTRIES = {"EU27_2020":"European Union (27)", "NO":"Norway", "DE":"Germany", "BE":"Belgium", "NL":"Netherlands", "DK":"Denmark", "SE":"Sweden", "FI":"Finland", "FR":"France", "ES":"Spain"}
ENDPOINT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/mar_go_qmc"
PARAMS = [("lang","en"),("freq","Q"),("unit","THS_T"),("cargo","RO_TOT"),("direct","TOTAL"),("sinceTimePeriod","2022-Q1")] + [("rep_mar", c) for c in COUNTRIES]
URL = ENDPOINT + "?" + urllib.parse.urlencode(PARAMS)
PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "shipping-roro-traffic.json"
DIMENSIONS = ["freq","unit","cargo","direct","rep_mar","time"]

def period_valid(p):
    return isinstance(p, str) and bool(re.fullmatch(r"\d{4}-Q[1-4]", p))

def number_valid(v):
    return isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0

def parse_payload(d):
    if d.get("source")!="ESTAT" or d.get("id")!=DIMENSIONS or d.get("size",[])[:4]!=[1,1,1,1] or len(d["size"])!=6:
        raise ValueError("Unexpected Eurostat dimensions")
    size=d["size"]
    if any(not isinstance(n,int) or n<1 for n in size):
        raise ValueError("Invalid dimensions")
    dim=d["dimension"]
    for k,v in {"freq":"Q","unit":"THS_T","cargo":"RO_TOT","direct":"TOTAL"}.items():
        if dim[k]["category"]["index"]!={v:0}:
            raise ValueError("Wrong classification: "+k)
    countries=dim["rep_mar"]["category"]["index"]
    times=dim["time"]["category"]["index"]
    if set(countries)!=set(COUNTRIES) or set(countries.values())!=set(range(size[4])) or set(times.values())!=set(range(size[5])) or not all(period_valid(p) for p in times):
        raise ValueError("Unexpected countries or periods")
    values=d["value"]
    status=d.get("status") or {}
    def at(obj,i):
        if isinstance(obj,list):
            return obj[i] if i<len(obj) else None
        return obj.get(str(i))
    result={}
    for country,i in countries.items():
        rows=[]
        for period,j in times.items():
            k=i*size[5]+j
            value=at(values,k)
            if number_valid(value):
                flag=at(status,k)
                rows.append({"period":period,"value":value,"flag":flag if isinstance(flag,str) else None})
        result[country]=sorted(rows,key=lambda p:p["period"])
    if not any(result.values()):
        raise ValueError("No usable observations")
    return result

def build_dataset(payload,previous,observed_on):
    latest=parse_payload(payload)
    old={s["countryCode"]:s for s in previous.get("series",[]) if isinstance(s,dict) and s.get("countryCode") in COUNTRIES}
    series=[]
    for c,name in COUNTRIES.items():
        # Replace only exact period observations returned by the source.
        merged={p["period"]:p for p in old.get(c,{}).get("history",[]) if isinstance(p,dict) and period_valid(p.get("period")) and number_valid(p.get("value"))}
        merged.update({p["period"]:p for p in latest[c]})
        if not merged:
            continue
        history=sorted(merged.values(),key=lambda p:p["period"])
        series.append({"key":"eurostat:mar_go_qmc:RO_TOT:"+c,"countryCode":c,"label":name,"unit":"thousand tonnes","frequency":"quarterly","period":history[-1]["period"],"value":history[-1]["value"],"history":history,
                       "lastSuccessfulRefresh":observed_on if latest[c] else old.get(c,{}).get("lastSuccessfulRefresh",previous.get("observedOn"))})
    return {"schemaVersion":1,"observedOn":observed_on,"sourceUpdated":payload.get("updated"),"provider":"Eurostat","datasetCode":"mar_go_qmc","sourceUrl":"https://ec.europa.eu/eurostat/databrowser/view/mar_go_qmc/default/table?lang=en","apiUrl":URL,"licenseUrl":"https://ec.europa.eu/eurostat/help/copyright-notice","license":"Eurostat statistical data reuse with attribution, subject to source-specific exceptions; EU/EFTA reporting entities selected.","notice":"Ro-Ro mobile self-propelled and non-self-propelled units, total direction, gross cargo weight handled at main ports. Not freight rates, pure vehicle exports, carrier utilization or issuer route exposure. Country series and EU aggregate overlap; do not sum. No imputation of unpublished quarters.","series":series}

def main():
    previous=json.loads(PATH.read_text(encoding="utf8")) if PATH.exists() else {}
    headers={"Accept":"application/json","User-Agent":"Nordl Stockwatch research collector/1.0"}
    with urllib.request.urlopen(urllib.request.Request(URL,headers=headers),timeout=45) as response:
        payload=json.load(response)
    data=build_dataset(payload,previous,dt.date.today().isoformat())
    target=PATH.with_suffix(".tmp")
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    target.replace(PATH)
    print(f"Eurostat Ro-Ro: {len(data['series'])} series, {sum(len(s['history']) for s in data['series'])} observations")

if __name__=="__main__":
    main()
