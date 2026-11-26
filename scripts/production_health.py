"""Read-only production canary. Report regressions separately from coverage targets."""
from __future__ import annotations
import argparse,json,re,sys,time
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
BASE="https://stocks.nordl.dev/"
API="https://stockwatch-research-api.gauchovidar.workers.dev/api/health"
PAGES=["","stocks.html","news.html","health.html","unlisted.html","company.html?ticker=NHY.OL","company.html?ticker=XNAS%3ANVDA","directory.html","terminal.html","shipping.html","spreads.html"]
LIMIT=12*1024*1024
class Head(HTMLParser):
    def __init__(self):super().__init__();self.canonical=[];self.robots=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="link" and a.get("rel")=="canonical":self.canonical.append(a.get("href"))
        if tag=="meta" and a.get("name","").lower() in ("robots","googlebot"):self.robots.append(a.get("content","").lower())
def fetch(url):
    for attempt in range(2):
        try:
            with urlopen(Request(url,headers={"User-Agent":"NordlProductionHealth/1.0 (+https://stocks.nordl.dev/)","Cache-Control":"no-cache"}),timeout=15) as r:
                if urlsplit(r.geturl()).hostname!=urlsplit(url).hostname:raise ValueError("unexpected host")
                raw=r.read(LIMIT+1)
                if len(raw)>LIMIT:raise ValueError("response size")
                return raw.decode("utf-8-sig"),dict((k.lower(),v) for k,v in r.headers.items())
        except Exception:
            if attempt:raise
            time.sleep(3)
ROOT=Path(__file__).resolve().parents[1]

def internal_gleif(root,now):
    """Validate retained repository mapping, not a public Pages endpoint."""
    folder=Path(root)/"data/gleif-isin-lei"
    idx=json.loads((folder/"index.json").read_text(encoding="utf-8"))
    match=re.fullmatch(r"data/gleif-isin-lei/([0-9]{4}-[0-9]{2}-[0-9]{2})-([a-f0-9]{16})(?:-[a-f0-9]{12})?\.json",idx["snapshot"])
    if not match:raise ValueError("invalid internal snapshot path")
    target=folder/Path(idx["snapshot"]).name
    if folder.is_symlink() or target.is_symlink() or (folder/"index.json").is_symlink():raise ValueError("unsafe internal mapping path")
    snap=json.loads(target.read_text(encoding="utf-8"))
    if idx.get("schemaVersion")!=1 or snap.get("schemaVersion")!=1 or snap.get("source")!="ANNA/GLEIF":
        raise ValueError("invalid mapping schema")
    if idx["sourceDate"]!=match[1] or snap["sourceDate"]!=match[1] or not re.fullmatch(r"[a-f0-9]{64}",snap["sha256"]) or not snap["sha256"].startswith(match[2]):
        raise ValueError("mapping provenance mismatch")
    records=snap["records"]
    counts={k:sum(r["status"]==k for r in records) for k in ("matched","ambiguous","unmatched")}
    if sum(counts.values())!=len(records) or len({r["isin"] for r in records})!=len(records):
        raise ValueError("invalid mapping records")
    for key,value in (("matchedISINs",counts["matched"]),("ambiguousISINs",counts["ambiguous"]),("eligibleISINs",len(records))):
        if idx[key]!=value or snap[key]!=value:raise ValueError("mapping count mismatch")
    if counts["matched"]<17:raise ValueError("GLEIF mapping baseline regression")
    last=datetime.fromisoformat(idx["lastSuccess"].replace("Z","+00:00"))
    age=(now-last).total_seconds()/3600
    if age < -1:raise ValueError("future GLEIF success")
    return {"matched":counts["matched"],"ageHours":round(age,1),"status":idx["status"]}

def audit(get=fetch,now=None,require_gleif=False,require_sec=False,local_root=ROOT):
    now=now or datetime.now(timezone.utc);issues=[];metrics={};checks=[]
    def issue(code,level,message):issues.append({"code":code,"severity":level,"message":message})
    def check(code,url,fn):
        try:
            body,headers=get(url);fn(body,headers);checks.append({"id":code,"ok":True})
        except Exception as e:
            issue(code,"critical",type(e).__name__+": "+str(e)[:200]);checks.append({"id":code,"ok":False})
    def require(ok,message):
        if not ok:raise ValueError(message)
    def data(code,path,fn):check(code,BASE+path,lambda body,h:fn(json.loads(body)))
    for p in PAGES:
        def page(body,h,p=p):
            require("<html" in body.lower(),"HTML missing")
            head=Head();head.feed(body)
            if "?" not in p:
                require(head.canonical==[BASE+p],"canonical mismatch")
                require(not any(re.search(r"\b(noindex|none)\b",s) for s in head.robots+[h.get("x-robots-tag","")]),"unexpected noindex")
            else:
                # Parameterized company workspaces are intentionally outside the sitemap.
                require("company research" in body.lower(),"company workspace shell missing")
        check("page:"+p,BASE+p,page)
    def robots(body,h):
        require("Sitemap: "+BASE+"sitemap.xml" in body,"sitemap directive missing")
        require(not re.search(r"(?im)^Disallow:\s*/\s*$",body),"root blocked")
    check("robots",BASE+"robots.txt",robots)
    def sitemap(body,h):
        urls=[n.text for n in ET.fromstring(body).findall("{*}url/{*}loc")]
        require(len(urls)>=17 and len(set(urls))==len(urls),"sitemap shrank or duplicate URLs")
        require(BASE in urls and all(u and u.startswith(BASE) for u in urls),"unexpected sitemap host")
        metrics["sitemapUrls"]=len(urls)
    check("sitemap",BASE+"sitemap.xml",sitemap)
    def coverage(d):
        s=d["summary"];rows=d["records"];ids=[r["id"] for r in rows]
        require(len(rows)==s["listings"] and len(set(ids))==len(ids),"listing denominator mismatch")
        require(s["priced"]+s["missingPrice"]==len(rows),"price denominator mismatch")
        require(sum(r["priceStatus"]!="missing" for r in rows)==s["priced"],"price row mismatch")
        monitored=[r for r in rows if r["group"]=="monitored"]
        require(len(rows)>=500 and len(monitored)>=139,"listing universe shrank")
        metrics.update({"listings":len(rows),"priced":s["priced"],"monitored":len(monitored),"missingPrice":s["missingPrice"]})
        if s["priced"]<152:issue("price_coverage_regression","critical","Below approved 152 priced baseline")
        if any(r["priceStatus"]=="missing" for r in monitored):issue("monitored_price_missing","critical","Existing monitored listing lost dated price")
        if s["missingPrice"]:metrics["knownPriceGap"]=s["missingPrice"]
    data("coverage","data/listing-coverage-v1.json",coverage)
    def signals(d):
        t=datetime.fromisoformat(d["generated"].replace("Z","+00:00"));age=(now-t).total_seconds()/3600
        require(-1<=age,"future snapshot")
        metrics["scanAgeHours"]=round(age,1)
        if age>96:issue("scan_stale","critical","Scanner older than 96 hours, including weekend observations")
        elif now.weekday()<5 and 8<=now.hour<=19 and age>3:
            issue("market_scan_overdue","warning","No successful scanner snapshot within 3 hours during weekday scan coverage")
        elif now.weekday()>=5 and 17<=now.hour<=20 and age>7:
            issue("weekend_scan_overdue","warning","Expected weekend refresh has not published within 7 hours")
        elif age>30 and now.weekday()<5 and now.weekday()!=0:
            issue("scan_stale","warning","Scanner older than 30 hours on trading weekday")
        require(len(d["companies"])>=139,"scanner listing count shrank")
    data("signals","data/signals.json",signals)
    def health(d):
        metrics["priceFreshness"]=d["priceFreshness"]["status"]
        eq=d["priceFreshness"].get("equities") or {}
        metrics["sessionComparable"]=eq.get("comparable")
        metrics["sessionUnconfirmed"]=eq.get("unconfirmed")
        if d["priceFreshness"]["status"]!="coverage_ok":issue("session_coverage","warning","Completed-session comparison coverage degraded; dated prices can still be present")
    data("source_health","data/source-health.json",health)
    def sec(d):
        rows=d["issuers"];require(len(rows)>=50,"SEC cohort shrank")
        n=sum(x["records"] for x in rows.values());metrics["secFinancialFacts"]=n
        require(n>=29155,"SEC financial history below baseline")
        for cik in ("0001045810","0000002488"):
            r=rows[cik];require(r["path"]=="data/sec-companyfacts/"+cik+".json","SEC path mismatch")
            def detail(x,cik=cik,r=r):
                require(x["cik"]==cik and len(x["records"])==r["records"],"SEC file identity/count mismatch")
            data("sec_file:"+cik,r["path"],detail)
        if any(x["status"]!="ok" for x in rows.values()):issue("sec_refresh","warning","One or more SEC refreshes degraded")
    if require_sec:data("sec_index","data/sec-companyfacts/index.json",sec)
    if require_gleif:
        try:
            state=internal_gleif(local_root,now)
            metrics["gleifMatched"]=state["matched"]
            metrics["gleifAgeHours"]=state["ageHours"]
            checks.append({"id":"gleif_internal_snapshot","ok":True})
            if state["status"]!="ok" or state["ageHours"]>72:
                issue("gleif_refresh","warning","Internal GLEIF mapping retained or older than 72 hours")
        except Exception as e:
            checks.append({"id":"gleif_internal_snapshot","ok":False})
            issue("gleif_internal_snapshot","critical",type(e).__name__+": "+str(e)[:200])
    def archive(body,h):
        d=json.loads(body);require(d.get("status")=="ok" and d.get("storage")=="d1","D1 unhealthy")
        require(d.get("articles",0)>=1640,"D1 record count below baseline");metrics["d1Articles"]=d["articles"]
    check("d1",API,archive)
    return {"generated":now.isoformat(),"status":"critical" if any(i["severity"]=="critical" for i in issues) else "degraded" if issues else "ok","checks":checks,"metrics":metrics,"issues":issues}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="production-health.json");p.add_argument("--require-sec",action="store_true");p.add_argument("--require-gleif",action="store_true");a=p.parse_args()
    d=audit(require_sec=a.require_sec,require_gleif=a.require_gleif)
    Path(a.output).write_text(json.dumps(d,indent=2)+"\n")
    print(json.dumps(d,indent=2))
if __name__=="__main__":main()
