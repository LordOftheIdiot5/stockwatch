"""Bounded official statistical and filing collection; no securities quotations."""
from __future__ import annotations
import argparse,json,math,os,time,re,hashlib,csv,io
from itertools import product
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
UA="StockwatchResearch/1.0 (+https://stocks.nordl.dev/)"
EU="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SSB="https://data.ssb.no/api/pxwebapi/v2/tables/"
SOD="https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer/"
SEC="https://data.sec.gov/api/xbrl/companyfacts/CIK"
USGS="https://www.sciencebase.gov/catalog/items"
COM="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
LICENSES={"eurostat":"Eurostat reuse policy; source attribution and dataset exceptions","ssb":"CC BY 4.0","sodir":"NLOD 2.0","sec":"SEC public filing content reuse policy","usgs":"CC0 for 2026 MCS parent release; child file review required"}
TERMS={"eurostat":"https://ec.europa.eu/eurostat/help/copyright-notice","ssb":"https://www.ssb.no/en/api","sodir":"https://www.sodir.no/en/facts/data-and-analyses/open-data/","sec":"https://www.sec.gov/about/webmaster-frequently-asked-questions","usgs":"https://www.usgs.gov/data/mineral-commodity-summaries-2026-data-release"}
LICENSES.update({"scb":"SCB open data CC0 / CC BY 4.0 attribution; exceptions apply","statfin":"CC BY 4.0","dst":"CC BY 4.0","riksbank":"Riksbank reference rates reuse with source attribution; not tradable prices","ecb":"ECB statistical reuse; attribution and third-party exceptions","norges_bank":"NLOD 2.0","world_bank":"CC BY 4.0; indicator exceptions"})
TERMS.update({"scb":"https://www.scb.se/en/api/","statfin":"https://stat.fi/en/about-us/get-to-know-statistics-finland/legislation/terms-of-use","dst":"https://www.dst.dk/en/Statistik/hjaelp-til-statistikbanken/api","riksbank":"https://www.riksbank.se/en-gb/statistics/interest-rates-and-exchange-rates/retrieving-interest-rates-and-exchange-rates-via-api/faq--the-api-for-interest-rates-and-exchange-rates/","ecb":"https://data.ecb.europa.eu/","norges_bank":"https://www.norges-bank.no/en/topics/Statistics/open-data/","world_bank":"https://data.worldbank.org/summary-terms-of-use"})
def stamp():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def number(x):return type(x) in (int,float) and math.isfinite(x)
def url(base,params):return base+"?"+urlencode(params,doseq=True)
def fetch(u,agent=UA):
    if urlsplit(u).scheme!="https":raise ValueError("HTTPS required")
    req=Request(u,headers={"User-Agent":agent,"Accept":"application/json"})
    with urlopen(req,timeout=35) as response:
        if urlsplit(response.geturl()).hostname!=urlsplit(u).hostname:raise ValueError("unexpected_redirect")
        raw=response.read(16_000_001)
    if len(raw)>16_000_000:raise ValueError("response_limit")
    return json.loads(raw)
def jsonstat(data,cap=30000):
    """Preserve every dimension and original code; no aggregation or zero filling."""
    ids=data["id"];sizes=data["size"]
    if not ids or len(ids)!=len(set(ids)) or len(ids)!=len(sizes) or any(type(n)!=int or n<1 for n in sizes) or math.prod(sizes)>cap:raise ValueError("invalid_dimensions")
    dims=[];axes=[]
    for k,n in zip(ids,sizes):
        d=data["dimension"][k];c=d["category"];idx=c["index"]
        ordered=idx if isinstance(idx,list) else [x for x,_ in sorted(idx.items(),key=lambda y:y[1])]
        if len(ordered)!=n or len(set(ordered))!=n or (isinstance(idx,dict) and sorted(idx.values())!=list(range(n))):raise ValueError("invalid_index")
        axes.append(ordered)
        dims.append({"id":k,"label":d.get("label",k),"labels":c.get("label",{}),"unit":c.get("unit",{})})
    values=data["value"];status=data.get("status",{})
    def at(v,i):
        if isinstance(v,list):return v[i] if i<len(v) else None
        if isinstance(v,dict):return v.get(str(i))
        return v if isinstance(v,str) else None
    records=[]
    for i,keys in enumerate(product(*axes)):
        v=at(values,i)
        if number(v):records.append({"coordinates":dict(zip(ids,keys)),"value":v,"status":at(status,i)})
    if not records:raise ValueError("no_numeric_observations")
    return {"title":data.get("label"),"sourceUpdated":data.get("updated"),"dimensions":dims,"records":records}
def eurostat(get):
    # Bounded geography and sector selections, actual official published monthly indices.
    u=url(EU+"sts_inpr_m",[("lang","EN"),("freq","M"),("indic_bt","PRD"),("s_adj","SCA"),("unit","I21"),("nace_r2","C"),("sinceTimePeriod","2021-01")]+[("geo",x) for x in ("EU27_2020","DE","FR","SE","DK","FI","NO","NL","IT","ES")])
    out=jsonstat(get(u))
    if any(x["coordinates"].get("nace_r2")!="C" or x["coordinates"].get("unit")!="I21" for x in out["records"]):raise ValueError("unexpected_selection")
    return u,out
def ssb(get):
    u=url(SSB+"07095/data",{"lang":"en","valueCodes[Tid]":"from(2021M01)","valueCodes[ContentsCode]":"*","outputFormat":"json-stat2"})
    return u,jsonstat(get(u))
def sodir(get,layer,fields,key,where="1=1"):
    base=SOD+str(layer)+"/query"
    params={"f":"json","where":where,"outFields":",".join(fields),"returnGeometry":"false","orderByFields":"OBJECTID ASC","resultRecordCount":1000}
    rows=[];seen=set()
    for offset in range(0,15000,1000):
        data=get(url(base,{**params,"resultOffset":offset}))
        if "error" in data or not isinstance(data.get("features"),list):raise ValueError("arcgis_error")
        for feature in data["features"]:
            a=feature["attributes"]
            if not all(k in a for k in fields) or a.get(key) is None or a[key] in seen:raise ValueError("unexpected_or_duplicate_asset")
            seen.add(a[key]);rows.append({k:a[k] for k in fields})
        if not data.get("exceededTransferLimit"):break
    else:raise ValueError("pagination_cap")
    if not rows:raise ValueError("empty_assets")
    return url(base,params),{"records":rows,"notice":"Reported source attributes; do not infer public issuer identity or ownership percentage."}
def sec_facts(data,cik,now=None):
    now=now or datetime.now(timezone.utc).date().isoformat()
    if str(data.get("cik")).lstrip("0")!=cik.lstrip("0"):raise ValueError("CIK mismatch")
    tags=("RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","NetIncomeLoss","OperatingIncomeLoss","Assets","Liabilities","StockholdersEquity","CashAndCashEquivalentsAtCarryingValue","NetCashProvidedByUsedInOperatingActivities","PaymentsToAcquirePropertyPlantAndEquipment","EarningsPerShareDiluted")
    rows=[]
    for tag in tags:
        entry=data.get("facts",{}).get("us-gaap",{}).get(tag,{})
        for unit,items in entry.get("units",{}).items():
            if unit not in ("USD","USD/shares"):continue
            for x in items:
                if x.get("form") not in ("10-Q","10-K","10-Q/A","10-K/A") or not number(x.get("val")):continue
                dates=[x.get("end"),x.get("filed"),x.get("start",x.get("end"))]
                if not all(isinstance(d,str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}",d) for d in dates):continue
                if not dates[2]<=dates[0]<=dates[1]<=now or dates[0]<"2020-01-01":continue
                acc=x.get("accn")
                if not isinstance(acc,str) or not re.fullmatch(r"\d{10}-\d{2}-\d{6}",acc):continue
                rows.append({"tag":tag,"unit":unit,"value":x["val"],"periodStart":x.get("start"),"periodEnd":x["end"],"filed":x["filed"],"form":x["form"],"accession":acc,
                "sourceUrl":"https://www.sec.gov/Archives/edgar/data/"+str(int(cik))+"/"+acc.replace("-","")+"/"+acc+"-index.htm"})
    if not rows:raise ValueError("no_filing_facts")
    if len(rows)>20000:raise ValueError("facts_limit")
    return {"issuer":data.get("entityName"),"cik":cik,"records":rows,"notice":"As-filed taxonomy facts; repeated/restated periods retained, no automatic quarter or TTM calculations."}
def sec(get):
    agent=os.getenv("STOCKWATCH_SEC_USER_AGENT","").strip()
    if "@" not in agent:raise PermissionError("declared_SEC_contact_required")
    cik="0001045810";u=SEC+cik+".json"
    return u,sec_facts(get(u,agent),cik)
def minerals(get):
    # Discover the official parent release's child inventory. No file guessing.
    u="https://www.sciencebase.gov/catalog/item/69837e43b66b01367d7ec7c7?format=json"
    data=get(u)
    if data.get("id")!="69837e43b66b01367d7ec7c7" or "Mineral Commodity Summaries 2026" not in str(data.get("title")):raise ValueError("unexpected_release")
    # The known source-verified collection and salient-statistics child can be
    # inventoried even if the generic child-list endpoint is unavailable.
    child=get("https://www.sciencebase.gov/catalog/item/69837ec8b66b01367d7ec7d9?format=json")
    if child.get("id")!="69837ec8b66b01367d7ec7d9" or "Mineral Commodity Summaries 2026" not in str(child.get("title")):raise ValueError("unexpected_child")
    items=[data,child]
    records=[{"id":x["id"],"title":x.get("title"),"sourceUrl":"https://www.sciencebase.gov/catalog/item/"+x["id"],"fileNames":[z.get("name") for z in x.get("files",[]) if isinstance(z.get("name"),str)]} for x in items if isinstance(x.get("id"),str) and re.fullmatch(r"[0-9a-f]{24}",x["id"])]
    if not records:raise ValueError("missing_catalog")
    return u,{"records":records,"notice":"USGS mineral release inventory only; CSV contents and child metadata not yet imported."}
def mineral_csv(raw,name,source_url):
    if len(raw)>2_000_000:raise ValueError("mineral_file_limit")
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline=""))
    header=reader.fieldnames or []
    if not header or len(header)>100 or len(header)!=len(set(header)) or any(not x.strip() for x in header):raise ValueError("invalid_csv_header")
    records=[]
    for row in reader:
        if None in row or any(v is None for v in row.values()):raise ValueError("malformed_csv")
        if len(records)>=20000:raise ValueError("mineral_row_limit")
        if any(v.strip() for v in row.values()):records.append({"table":name,"sourceUrl":source_url,"fields":row})
    if not records:raise ValueError("empty_csv")
    return records,header

def mineral_download(u):
    p=urlsplit(u)
    if p.scheme!="https" or p.hostname not in ("www.sciencebase.gov","sciencebase.gov") or not p.path.startswith("/catalog/file/"):raise ValueError("unreviewed_file_url")
    req=Request(u,headers={"User-Agent":UA,"Accept":"text/csv,application/octet-stream"})
    with urlopen(req,timeout=40) as response:
        dest=urlsplit(response.geturl())
        if dest.scheme!="https" or dest.hostname not in ("www.sciencebase.gov","sciencebase.gov"):raise ValueError("unexpected_file_redirect")
        data=response.read(2_000_001)
    if len(data)>2_000_000:raise ValueError("mineral_file_limit")
    return data

def mineral_statistics(get,download=mineral_download):
    child_id="69837ec8b66b01367d7ec7d9"
    u="https://www.sciencebase.gov/catalog/item/"+child_id+"?format=json"
    d=get(u)
    if d.get("id")!=child_id or "Mineral Commodity Summaries 2026" not in str(d.get("title")):raise ValueError("unexpected_child")
    files=d.get("files") or []
    selected=[f for f in files if isinstance(f.get("name"),str) and f["name"].lower().endswith(".csv")]
    if not selected:raise ValueError("no_csv_files_in_child")
    if len(selected)>32:raise ValueError("mineral_file_count_limit")
    rows=[];tables=[]
    for f in sorted(selected,key=lambda x:x["name"]):
        name=f["name"];link=f.get("url","")
        p=urlsplit(link)
        if child_id not in link or p.scheme!="https" or p.hostname not in ("www.sciencebase.gov","sciencebase.gov") or not p.path.startswith("/catalog/file/"):raise ValueError("unexpected_file_identity")
        raw=download(link)
        data,header=mineral_csv(raw,name,link)
        rows.extend(data);tables.append({"file":name,"columns":header,"rows":len(data),"sha256":hashlib.sha256(raw).hexdigest(),"sourceUrl":link})
        if len(rows)>40000:raise ValueError("aggregate_mineral_row_limit")
        time.sleep(.35)
    return u,{"title":d.get("title"),"records":rows,"tables":tables,"license":"USGS public domain / CC0 2026 MCS release","metadataUrl":"https://data.usgs.gov/datacatalog/metadata/USGS.69837ec8b66b01367d7ec7d9.xml","notice":"Original CSV strings preserved, including unit labels, estimates, suppression and footnote codes; no numeric conversion or cross-mineral aggregation."}

def comtrade_probe(get):
    u=url(COM,{"reporterCode":276,"period":2025,"partnerCode":0,"cmdCode":"8703","flowCode":"X"})
    d=get(u);rows=d.get("data") or []
    valid=[x for x in rows if x.get("reporterCode")==276 and str(x.get("period"))=="2025" and str(x.get("cmdCode"))=="8703" and x.get("partnerCode")==0 and x.get("flowCode")=="X" and number(x.get("primaryValue"))]
    if not valid:raise ValueError("no_matching_preview")
    return {"status":"probe_ok","matchedRows":len(valid),"sourceUrl":u,"publication":"No trade records stored; commercial API and redistribution review required."}
def build(root=ROOT,get=fetch,probe=False):
    folder=root/"data";target=folder/"free-research.json"
    try:old=json.loads(target.read_text())
    except (OSError,ValueError):old={}
    prior={x["id"]:x for x in old.get("datasets",[]) if isinstance(x,dict) and "id" in x}
    cfg=[
      ("eurostat-production","eurostat",lambda:eurostat(get)),
      ("ssb-production","ssb",lambda:ssb(get)),
      ("sodir-fields","sodir",lambda:sodir(get,7100,["fldNpdidField","fldName","fldCurrentActivitySatus","cmpLongName","cmpNpdidCompany","fldHcType","fldMainArea","fldDateUpdatedMax"],"fldNpdidField")),
      ("sodir-owner-history","sodir",lambda:sodir(get,7111,["fldOwnerHstGUID","fldNpdidField","fldNpdidOwner","fldOwnerName","fldOwnerKind","fldOwnershipFromDate","fldOwnershipToDate","fldOwnerDateUpdated"],"fldOwnerHstGUID")),
      ("sec-nvda","sec",lambda:sec(get)),
      ("usgs-minerals-index","usgs",lambda:minerals(get)),
      ("usgs-mineral-statistics","usgs",lambda:mineral_statistics(get))]
    from nordic_sources import configuration
    cfg.extend(configuration())
    datasets=[];blocked=set()
    for id,provider,collect in cfg:
        try:
            if provider in blocked:raise PermissionError("provider_stopped")
            u,payload=collect()
            row={"id":id,"provider":provider,"sourceUrl":u,"license":LICENSES[provider],"termsUrl":TERMS[provider],"retrievedAt":stamp(),"status":"ok",**payload}
        except Exception as e:
            if isinstance(e,HTTPError) and e.code in (401,403,429):blocked.add(provider)
            row={**prior.get(id,{"id":id,"provider":provider,"records":[],"license":LICENSES[provider],"termsUrl":TERMS[provider]}),"status":"stale" if prior.get(id,{}).get("records") else "unavailable","errorType":type(e).__name__,"checkedAt":stamp()}
            if isinstance(e,HTTPError):row["httpStatus"]=e.code
        datasets.append(row)
        print("FREE_DATA "+json.dumps({"id":id,"status":row["status"],"records":len(row["records"]),"error":row.get("errorType"),"httpStatus":row.get("httpStatus"),"tables":len(row.get("tables",[]))}),flush=True)
        time.sleep(.35)
    try:trade=comtrade_probe(get)
    except Exception as e:trade={"status":"unavailable","errorType":type(e).__name__}
    print("COMTRADE_PROBE "+json.dumps(trade),flush=True)
    out={"schemaVersion":1,"generated":stamp(),"datasets":datasets,"restrictedSourceChecks":{"comtrade":trade,"imf":{"status":"permission_required","sourceUrl":"https://www.imf.org/en/About/copyright-and-terms","reason":"Request commercial reuse permission before systematic production ingestion"}},"notice":"Official source observations, not live market quotes; per-source conditions and dates apply."}
    if not probe:
        folder.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix(".tmp");tmp.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n");tmp.replace(target)
        cat=folder/"dataset-catalog.json"
        try:catalog=json.loads(cat.read_text())
        except (OSError,ValueError):catalog={"datasets":[]}
        catalog["datasets"]=[x for x in catalog.get("datasets",[]) if x.get("path")!="data/free-research.json"]+[{"name":"Official industry, assets, filings and mineral research","path":"data/free-research.json","records":sum(len(x["records"]) for x in datasets),"license":"Per-dataset source terms; Comtrade preview metadata only"}]
        catalog["generated"]=stamp();cat.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n")
    return out
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--probe",action="store_true");a=p.parse_args();build(probe=a.probe)
