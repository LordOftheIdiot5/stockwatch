"""OECD broad-market monthly share-price source preflight. No values published."""
import csv,io,json,math,re
from collections import defaultdict
from datetime import date
from urllib.request import Request,urlopen
SOURCE="https://www.oecd.org/en/data/indicators/share-prices.html"
TERMS="https://www.oecd.org/en/about/terms-conditions.html"
URL="https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/.M.SHARE.IX.....?startPeriod=2025-01&format=csvfile"
REQUIRED={"REF_AREA","FREQ","MEASURE","UNIT_MEASURE","ACTIVITY","ADJUSTMENT","TRANSFORMATION","TIME_HORIZON","METHODOLOGY","TIME_PERIOD","OBS_VALUE","OBS_STATUS","UNIT_MULT","BASE_PER"}
def inspect(raw,today=None):
    today=today or date.today()
    r=csv.DictReader(io.StringIO(raw))
    if not REQUIRED<=set(r.fieldnames or []):raise ValueError("unexpected SDMX CSV header")
    groups=defaultdict(dict);rejected=0
    for row in r:
        if None in row or None in row.values():raise ValueError("malformed row")
        if (row["FREQ"],row["MEASURE"],row["UNIT_MEASURE"],row["ACTIVITY"],row["ADJUSTMENT"],row["TRANSFORMATION"],row["TIME_HORIZON"],row["METHODOLOGY"])!=("M","SHARE","IX","_Z","_Z","_Z","_Z","N"):
            rejected+=1;continue
        area=row["REF_AREA"];period=row["TIME_PERIOD"]
        if not re.fullmatch("[A-Z0-9_]{2,12}",area) or not re.fullmatch("[0-9]{4}-[0-9]{2}",period) or date.fromisoformat(period+"-01")>today:raise ValueError("invalid area or period")
        # Keep the 2015-base index without rescaling. Missing or other bases stay outside the probe.
        if row["UNIT_MULT"]!="0" or row["BASE_PER"]!="2015" or not row["OBS_VALUE"]:
            rejected+=1;continue
        value=float(row["OBS_VALUE"])
        if not math.isfinite(value) or value<=0:raise ValueError("invalid index")
        if period in groups[area] and groups[area][period]!=value:raise ValueError("conflicting index observation")
        groups[area][period]=value
        if len(groups)>100:raise ValueError("area bound")
    if not groups:raise ValueError("no qualifying series")
    return {"source":SOURCE,"sourceTerms":TERMS,"frequency":"monthly","unit":"2015=100","referenceAreas":len(groups),"observations":sum(len(g) for g in groups.values()),"coverage":[{"area":a,"first":min(g),"last":max(g),"observations":len(g)} for a,g in sorted(groups.items())],"excludedRows":rejected,"publishedValues":0,"rightsStatus":"individual_source_review_required","notice":"Monthly averages, not daily closing exchange benchmarks. OECD terms have exceptions for third-party ownership; no public observations until source-level rights reviewed."}
def main():
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"text/csv"}),timeout=60) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(4*1024**2+1)
    if len(raw)>4*1024**2:raise ValueError("response bound")
    print("OECD_SHARE_PRICE_PREFLIGHT "+json.dumps(inspect(raw.decode("utf-8-sig")),sort_keys=True))
if __name__=="__main__":main()
