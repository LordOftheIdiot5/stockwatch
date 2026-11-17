"""Bounded public statistical imports. Preserve original source dimensions and period codes."""
import csv,io,json,math,re
from datetime import date,timedelta
from urllib.request import Request,urlopen
from urllib.parse import urlencode,urlsplit
from free_research import jsonstat,number,UA,url

SCB="https://statistikdatabasen.scb.se/api/v2/tables/TAB4894"
FIN="https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ttvi/14mh.px"
DK="https://api.statbank.dk/v1/"
RIX="https://api.riksbank.se/swea/v1/Observations/"
ECB="https://data-api.ecb.europa.eu/service/data/"
def raw(u,body=None,accept="application/json",cap=8000000):
    req=Request(u,data=json.dumps(body).encode() if body is not None else None,headers={"User-Agent":UA,"Accept":accept,"Content-Type":"application/json"})
    with urlopen(req,timeout=35) as r:
        if urlsplit(r.geturl()).hostname!=urlsplit(u).hostname:raise ValueError("unexpected_redirect")
        b=r.read(cap+1)
    if len(b)>cap:raise ValueError("response_limit")
    return b
def get_json(u,body=None):return json.loads(raw(u,body))
def scb(get=get_json):
    # All three dimensions on TAB4894 are mandatory. Read the actual
    # dimension identifiers and period codes instead of assuming "Tid".
    meta=get(url(SCB+"/metadata",{"lang":"en"}))
    ids=meta["id"];dims=meta["dimension"]
    if len(ids)!=3:raise ValueError("unexpected_scb_dimensions")
    params={"lang":"en","outputFormat":"json-stat2"}
    size=1;period_id=None
    for k in ids:
        cat=dims[k]["category"];idx=cat["index"]
        codes=idx if isinstance(idx,list) else [x for x,_ in sorted(idx.items(),key=lambda x:x[1])]
        if not codes or len(codes)!=len(set(codes)):raise ValueError("invalid_scb_codes")
        if all(re.fullmatch(r"\d{4}M\d{2}",x) for x in codes):
            if period_id:raise ValueError("ambiguous_scb_period")
            period_id=k;codes=sorted(codes)[-24:]
        size*=len(codes)
        params["valueCodes["+k+"]"]=",".join(codes)
    if not period_id or size>30000:raise ValueError("invalid_scb_selection")
    u=url(SCB+"/data",params)
    out=jsonstat(get(u))
    if {x["id"] for x in out["dimensions"]}!=set(ids):raise ValueError("unexpected_scb_response")
    out["tableId"]="TAB4894"
    out["notice"]="Production value index and development measures retain original statistical dimensions; do not combine index and percent values."
    return u,out
def fin(get=get_json):
    meta=get(FIN)
    variables=meta.get("variables",[])
    if len(variables)!=3:raise ValueError("unexpected_industry_dimensions")
    q=[]
    for v in variables:
        values=v["values"];labels=v["valueTexts"]
        if len(values)!=len(labels):raise ValueError("invalid_labels")
        if v.get("time") or all(re.fullmatch(r"\d{4}M\d{2}",x) for x in values):
            selected=values[-60:]
        else:
            # Preserve all named industries and statistical measures.
            selected=values
        q.append({"code":v["code"],"selection":{"filter":"item","values":selected}})
    if math.prod(len(x["selection"]["values"]) for x in q)>30000:raise ValueError("request_too_large")
    return FIN,jsonstat(get(FIN,{"query":q,"response":{"format":"json-stat2"}}))
def denmark(get=get_json):
    meta=get(DK+"tableinfo",{"table":"IPOP21","lang":"en"})
    variables=meta.get("variables",[])
    if len(variables)!=3:raise ValueError("unexpected_industry_dimensions")
    q=[]
    for v in variables:
        vals=[x["id"] for x in v["values"]]
        if not vals:raise ValueError("missing_values")
        if v.get("time") or all(re.fullmatch(r"\d{4}M\d{2}",x) for x in vals):vals=sorted(vals)[-60:]
        q.append({"code":v["id"],"values":vals})
    if math.prod(len(x["values"]) for x in q)>30000:raise ValueError("request_too_large")
    u=DK+"data"
    return u,jsonstat(dk_jsonstat(get(u,{"table":"IPOP21","format":"JSONSTAT","lang":"en","variables":q})))
def dk_jsonstat(payload):
    # StatBank documents JSON-stat; accepts v2 or a single v1 dataset.
    if isinstance(payload,dict) and "id" in payload and "size" in payload:return payload
    if not isinstance(payload,dict):raise ValueError("invalid_statbank_response")
    candidates=[x for x in payload.values() if isinstance(x,dict) and isinstance(x.get("dimension"),dict) and "value" in x]
    if len(candidates)!=1:raise ValueError("ambiguous_statbank_response")
    x=candidates[0];d=x["dimension"]
    if not isinstance(d.get("id"),list) or not isinstance(d.get("size"),list):raise ValueError("missing_statbank_dimensions")
    return {**x,"id":d["id"],"size":d["size"],"dimension":{k:d[k] for k in d["id"]}}
def dated_records(rows,date_key,value_key):
    out={}
    for r in rows:
        d=r.get(date_key);v=r.get(value_key)
        if not isinstance(d,str) or not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?",d):continue
        try:
            if isinstance(v,bool):continue
            n=float(v)
            date.fromisoformat(d if len(d)==10 else d+"-01")
        except (ValueError,TypeError):continue
        if not math.isfinite(n):continue
        if d in out and out[d]!=n:raise ValueError("conflicting_observations")
        out[d]=n
    if not out:raise ValueError("empty_series")
    return [{"date":d,"value":v} for d,v in sorted(out.items())]
def riksbank(code,label,unit,get=get_json):
    today=date.today();start=today-timedelta(days=730)
    u=RIX+code+"/"+start.isoformat()+"/"+today.isoformat()
    x=get(u)
    if not isinstance(x,list):raise ValueError("invalid_riksbank_response")
    return u,{"title":label,"unit":unit,"records":dated_records(x,"date","value")}
def sdmx(u,label,unit,reader=raw):
    b=reader(u,accept="text/csv",cap=8000000)
    rows=list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
    if not rows or len(rows)>10000:raise ValueError("invalid_sdmx_response")
    return u,{"title":label,"unit":unit,"records":dated_records(rows,"TIME_PERIOD","OBS_VALUE")}
def ecb_policy():
    return sdmx(ECB+"FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=2021-01-01","ECB deposit facility rate (daily observations)","percent per annum")
def ecb_lending():
    return sdmx(ECB+"MIR/M.U2.B.A2I.AM.R.A.2240.EUR.N?format=csvdata&startPeriod=2021-01","Euro area cost of borrowing by corporations (new business)","percent per annum")
def nb_policy():
    return sdmx("https://data.norges-bank.no/api/data/IR/B.KPRA.SD?format=csvfile&locale=en&startPeriod=2021-01-01","Norges Bank policy rate","percent per annum")
def wb_industry(get=get_json):
    u="https://api.worldbank.org/v2/country/NO;SE;DK;FI;DE;FR;GB;US;CN/indicator/NV.IND.MANF.ZS?format=json&date=2010:2026&per_page=500"
    payload=get(u)
    if not isinstance(payload,list) or len(payload)!=2:raise ValueError("invalid_world_bank_response")
    rows=[{"country":x.get("countryiso3code"),"period":x.get("date"),"value":x["value"]} for x in payload[1] if x.get("indicator",{}).get("id")=="NV.IND.MANF.ZS" and number(x.get("value")) and x.get("countryiso3code") in ("NOR","SWE","DNK","FIN","DEU","FRA","GBR","USA","CHN")]
    if not rows:raise ValueError("empty_series")
    return u,{"title":"Manufacturing value added","unit":"% of GDP","records":rows}
def configuration():
    return [
        ("scb-production","scb",scb),("finland-production","statfin",fin),("denmark-production","dst",denmark),
        ("riksbank-policy","riksbank",lambda:riksbank("SECBREPOEFF","Swedish policy rate","percent per annum")),
        ("riksbank-eur","riksbank",lambda:riksbank("SEKEURPMI","EUR reference rate","SEK per EUR")),
        ("riksbank-nok","riksbank",lambda:riksbank("SEKNOKPMI","NOK reference rate","SEK per NOK")),
        ("ecb-deposit","ecb",ecb_policy),("ecb-corporate-lending","ecb",ecb_lending),("norges-bank-policy","norges_bank",nb_policy),
        ("world-bank-manufacturing","world_bank",wb_industry)]
