"""Verify GitHub Pages serves this deployment's HTML, not a stale prior build."""
import argparse,hashlib,re,sys,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://stocks.nordl.dev/"
PATHS=("index.html","stocks.html","company.html","calendar.html","price-history.html","health.html",
       "v4.js","research.js","freshness-v96.css","overview-parity-v98.css",
       "global-market-pulse.js","heatmap-experience-v93.js",
       "overview-watchlist-v99.js","overview-watchlist-v99.css",
       "price-evidence-v97.js","price-evidence-v97.css",
       "overview-target-v110.css","workspace-density-v110b.css","workspace-density-v110b.js","overview-structure-v110d.css","overview-structure-v110d.js","overview-geo-v110e.css","overview-geo-v110e.js","brand/world-land-ne110.svg",
       "company-cockpit-v110c.css","company-cockpit-v110c.js",
       "terminal.html","shipping.html","commodities.html","spreads.html","intelligence.html","compare.html",
       "news.html","nasdaq-notices-v100.js","nasdaq-notices-v100.css")
TITLE=re.compile(rb"<title>(.*?)</title>",re.I|re.S)

def matched(local,remote):
    """Pages serves static files; compare bytes to catch stale code and cache."""
    return local==remote

def check(base=BASE,attempts=12,interval=10,fetch=None):
    if base!=BASE:raise ValueError("Production origin must be exact")
    if fetch is None:
        def fetch(path,attempt):
            url=base+path+"?"+urlencode({"deployment_check":str(attempt)+"-"+str(int(time.time()))})
            req=Request(url,headers={"Cache-Control":"no-cache","Pragma":"no-cache","User-Agent":"Stockwatch-Release-Verification/1.0"})
            with urlopen(req,timeout=15) as r:
                if r.geturl().split("?")[0]!=base+path:raise ValueError("Unexpected public release redirect")
                return r.read(2*1024*1024)
    expected={p:(ROOT/p).read_bytes() for p in PATHS}
    for n in range(1,attempts+1):
        statuses={}
        for path,blob in expected.items():
            try:
                actual=fetch(path,n)
                statuses[path]={"match":matched(blob,actual),"expectedSHA256":hashlib.sha256(blob).hexdigest()[:12],"actualSHA256":hashlib.sha256(actual).hexdigest()[:12]}
            except Exception as e:
                statuses[path]={"match":False,"error":type(e).__name__}
        if all(v["match"] for v in statuses.values()):
            print(f"Stockwatch release verified: all {len(PATHS)} public HTML and application asset files exactly match deployed artifact",statuses,flush=True)
            return statuses
        print("Public deployment not consistent yet:",n,statuses,flush=True)
        if n<attempts:time.sleep(interval)
    raise RuntimeError("Public GitHub Pages files do not match this deployment; investigate Pages workflow/caching before claiming live")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--attempts",type=int,default=12);p.add_argument("--interval",type=int,default=10);a=p.parse_args()
    if a.attempts<1 or a.attempts>25 or a.interval<0 or a.interval>30:raise SystemExit("Invalid retry bound")
    check(attempts=a.attempts,interval=a.interval)
