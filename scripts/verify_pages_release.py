"""Verify GitHub Pages serves this deployment's HTML, not a stale prior build."""
import argparse,hashlib,re,sys,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
BASE="https://stocks.nordl.dev/"
PATHS=("index.html","stocks.html","company.html","calendar.html","price-history.html","health.html",
       "v4.js","research.js","freshness-v96.css","overview-parity-v98.css",
       "global-market-pulse.js","heatmap-experience-v93.js",
       "overview-watchlist-v99.js","overview-header-v116b.js","overview-unified-v116c.js","overview-watchlist-v99.css",
       "price-evidence-v97.js","price-evidence-v97.css",
       "overview-target-v110.css","overview-firstfold-v116.css","overview-density-v116b.css","overview-unified-v116c.css","news-compact-v116.css","workspace-density-v110b.css","workspace-density-v110b.js","overview-structure-v110d.css","overview-structure-v110d.js","overview-geo-v110e.css","overview-geo-v110e.js","brand/world-land-ne110.svg","directory.html","research.html","search.html","data-products.html","brand/data-portal.js","brand/data-portal.css","welcome.html","brand/workspace-navigation-v112.css","brand/workspace-navigation-v112.js",
       "company-cockpit-v110c.css","company-cockpit-v110c.js","company-workflow-v113.js","core-research-v113.css","native-chart.js","terminal.js","secondary-markets-v114.js","secondary-markets-v114.css","shorts.html",
       "terminal.html","shipping.html","shipping-atlas-v118.js","shipping-mapfirst-v119.js","shipping-mapfirst-v119.css","shipping-map-polish-v119b.css","shipping-market-pulse-v121.mjs","shipping-market-pulse-v121.css","scripts/maritime-pulse-v121.mjs",
       "brand/world-land-ne50-v119c.svg","brand/world-borders-ne50-v119c.svg","data/shipping-world-borders-v119.json",
       "commodities.html","spreads.html","intelligence.html","compare.html",
       "news.html","nasdaq-notices-v100.js","nasdaq-notices-v100.css",
       "unlisted.html","unlisted-n41.css","unlisted-n41.js","shell-v47.js")
EXCLUDED_PATHS=("docs/NORDL-N04-ARCHIVE-CONTRACT.md","scripts/nordl-private-storage-v122.mjs","tests/test_nordl_runtime_v122.mjs","database/0001_core.sql","data/seen.json")
TITLE=re.compile(rb"<title>(.*?)</title>",re.I|re.S)

def matched(local,remote):
    """Pages serves static files; compare bytes to catch stale code and cache."""
    return local==remote

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def exclusion_status(base,path,attempt,*,opener=None):
    """Only direct not-found/gone is accepted. Never read private response bodies."""
    if base!=BASE or path not in EXCLUDED_PATHS:raise ValueError("Unexpected exclusion probe")
    opener=opener or build_opener(NoRedirect()).open
    url=base+path+"?"+urlencode({"deployment_check":str(attempt)+"-"+str(int(time.time()))})
    req=Request(url,headers={"Cache-Control":"no-cache","Pragma":"no-cache","User-Agent":"Stockwatch-Release-Verification/1.0"})
    try:
        with opener(req,timeout=15) as response:
            if response.geturl()!=url:raise ValueError("Unexpected exclusion redirect")
            return response.status
    except HTTPError as error:
        try:
            if error.geturl()!=url:raise ValueError("Unexpected exclusion redirect")
            return error.code
        finally:error.close()

def check(base=BASE,attempts=12,interval=10,fetch=None,probe=None):
    if base!=BASE:raise ValueError("Production origin must be exact")
    if fetch is None:
        def fetch(path,attempt):
            url=base+path+"?"+urlencode({"deployment_check":str(attempt)+"-"+str(int(time.time()))})
            req=Request(url,headers={"Cache-Control":"no-cache","Pragma":"no-cache","User-Agent":"Stockwatch-Release-Verification/1.0"})
            with urlopen(req,timeout=15) as r:
                if r.geturl().split("?")[0]!=base+path:raise ValueError("Unexpected public release redirect")
                return r.read(2*1024*1024)
    if probe is None:probe=lambda path,n:exclusion_status(base,path,n)
    expected={p:(ROOT/p).read_bytes() for p in PATHS}
    for n in range(1,attempts+1):
        statuses={}
        for path,blob in expected.items():
            try:
                actual=fetch(path,n)
                statuses[path]={"match":matched(blob,actual),"expectedSHA256":hashlib.sha256(blob).hexdigest()[:12],"actualSHA256":hashlib.sha256(actual).hexdigest()[:12]}
            except Exception as e:
                statuses[path]={"match":False,"error":type(e).__name__}
        for path in EXCLUDED_PATHS:
            try:
                status=probe(path,n)
                statuses[path]={"match":status in (404,410),"excluded":True,"status":status}
            except Exception as e:
                statuses[path]={"match":False,"excluded":True,"error":type(e).__name__}
        if all(v["match"] for v in statuses.values()):
            print(f"Stockwatch release verified: all {len(PATHS)} public HTML and application asset files exactly match deployed artifact; {len(EXCLUDED_PATHS)} excluded paths return 404/410",statuses,flush=True)
            return statuses
        print("Public deployment not consistent yet:",n,statuses,flush=True)
        if n<attempts:time.sleep(interval)
    raise RuntimeError("Public GitHub Pages files do not match this deployment; investigate Pages workflow/caching before claiming live")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--attempts",type=int,default=12);p.add_argument("--interval",type=int,default=10);a=p.parse_args()
    if a.attempts<1 or a.attempts>25 or a.interval<0 or a.interval>30:raise SystemExit("Invalid retry bound")
    check(attempts=a.attempts,interval=a.interval)
