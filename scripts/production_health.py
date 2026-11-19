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
PAGES=["","stocks.html","news.html","health.html","company.html?ticker=NHY.OL","company.html?ticker=XNAS%3ANVDA","directory.html","terminal.html","shipping.html","spreads.html"]
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
def audit(get=fetch,now=None,require_gleif=False,require_sec=False):
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
        if age>96:issue("scan_stale","critical","Scanner older than 96 hours (weekend-safe threshold)")
        elif age>30 and now.weekday()<5 and now.weekday()!=0:issue("scan_stale","warning","Scanner older than 30 hours on trading weekday")
        require(len(d["companies"])>=139,"scanner listing count shrank")
    data("signals","data/signals.json",signals)
    def health(d):
        metrics["priceFreshness"]=d["priceFreshness"]["status"]
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
    def gleif(d):
        require(d["snapshot"].startswith("data/gleif-isin-lei/") and d["snapshot"].endswith(".json") and ".." not in d["snapshot"],"invalid snapshot path")
        metrics["gleifMatched"]=d["matchedISINs"];require(d["matchedISINs"]>=17,"GLEIF mapping baseline regression")
        if d["status"]!="ok":issue("gleif_refresh","warning","GLEIF refresh degraded; retained snapshot")
        data("gleif_snapshot",d["snapshot"],lambda s:require(s["matchedISINs"]==d["matchedISINs"],"snapshot count mismatch"))
    if require_gleif:data("gleif_index","data/gleif-isin-lei/index.json",gleif)
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
