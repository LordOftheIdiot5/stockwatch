"""Secondary TWSE open-data snapshot collector; manual private staging only."""
import argparse,json,re
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from free_research import fetch,ROOT

URL="https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
DATASET="https://data.gov.tw/en/datasets/11549"
LICENSE="https://data.gov.tw/en/license"

def normalize(rows,as_of):
    if not isinstance(rows,list) or not 1<=len(rows)<=10000:raise ValueError("invalid snapshot")
    days=set();seen=set();bars=[];missing=0
    for r in rows:
        raw=r["Date"]
        if not isinstance(raw,str) or not re.fullmatch(r"\d{7}",raw):raise ValueError("invalid ROC date")
        day=date(int(raw[:3])+1911,int(raw[3:5]),int(raw[5:])).isoformat()
        if day>as_of:raise ValueError("future snapshot")
        days.add(day)
        symbol=r["Code"].strip();name=r["Name"].strip()
        if not re.fullmatch(r"[A-Z0-9]{1,12}",symbol) or not name or symbol in seen:
            raise ValueError("invalid or duplicate symbol")
        seen.add(symbol)
        prices=[r[k].strip().replace(",","") for k in ("OpeningPrice","HighestPrice","LowestPrice","ClosingPrice")]
        if any(x in ("","--","---") for x in prices):
            missing+=1;continue
        try:o,h,l,c=map(Decimal,prices)
        except InvalidOperation:raise ValueError("invalid price") from None
        if not all(x.is_finite() for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:
            raise ValueError("invalid OHLC")
        v=r["TradeVolume"].strip().replace(",","")
        if not re.fullmatch(r"\d+",v):raise ValueError("invalid volume")
        bars.append({"symbol":symbol,"name":name,"date":day,"mic":"XTAI","currency":"TWD",
                     "open":str(o),"high":str(h),"low":str(l),"close":str(c),"volumeShares":int(v)})
    if len(days)!=1 or not bars:raise ValueError("mixed dates or no observations")
    day=next(iter(days))
    return {"source":URL,"dataset":DATASET,"license":"Open Government Data License v1.0",
            "licenseUrl":LICENSE,"attribution":f"Securities and Futures Bureau, Financial Supervisory Commission / Taiwan Stock Exchange ({day[:4]}), Daily Trading Information of Listed Stocks, snapshot {day}. Made available under Open Government Data License v1.0.",
            "date":day,"retrievedAt":datetime.now(timezone.utc).isoformat(),
            "records":bars,"sourceRows":len(rows),"rowsMissingOHLC":missing,
            "corporateActionAdjusted":False,"publicationEnabled":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    out=a.output_dir.expanduser().resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError("stage outside repository")
    result=normalize(fetch(URL),datetime.now(timezone.utc).date().isoformat())
    out.mkdir(parents=True,exist_ok=True)
    dest=out/("twse-"+result["date"]+".json")
    # Never silently overwrite a prior dated snapshot; permit identical reruns.
    if dest.exists():
        prior=json.loads(dest.read_text(encoding="utf-8"))
        if prior["records"]!=result["records"]:raise ValueError("snapshot revision requires review")
    else:
        with dest.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,allow_nan=False)
    print(json.dumps({"date":result["date"],"records":len(result["records"]),"publicationEnabled":False}))

if __name__=="__main__":main()
