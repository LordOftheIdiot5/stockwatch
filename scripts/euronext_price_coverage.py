"""One bounded previous-day Euronext trade-report coverage probe.
Counts exact ISIN/MIC matches, never treats transaction reports as official closes.
No persistent price data or trade values are written.
"""
import csv,hashlib,io,json,re,zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from delayed_exchange import eur_url,downloaded,REQUIRED,MAX_EXPANDED
from exchange_identity import valid_isin
ROOT=Path(__file__).resolve().parents[1]
MARKETS={"XOSL":"OSL","XPAR":"PAR","XAMS":"AMS","XBRU":"BRU","XDUB":"DUB","XLIS":"LIS","XMIL":"MIL"}
def targets(queue):
    rows=queue["queues"]["euronext"]["records"];groups=defaultdict(dict)
    seen=set()
    for r in rows:
        isin=r.get("isin");mic=r.get("mic");id_=r["id"]
        if id_ in seen:raise ValueError("duplicate target")
        seen.add(id_)
        if r.get("identityStatus")!="isin_and_mic" or mic not in MARKETS or not valid_isin(isin):continue
        groups[MARKETS[mic]].setdefault((isin,mic),[]).append(id_)
    return groups,len(rows)
def parse(raw,expected):
    counts=Counter();identities=Counter();dates=Counter();matched_dates=Counter()
    seen=set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>MAX_EXPANDED:raise ValueError("invalid report archive")
        with z.open(files[0]) as stream,io.TextIOWrapper(stream,encoding="utf-8-sig",newline="") as f:
            reader=None
            for _ in range(4):
                line=f.readline()
                if not line:break
                for sep in (",",";","\t"):
                    fields=next(csv.reader([line],delimiter=sep))
                    if REQUIRED<=set(fields):
                        if len(fields)!=len(set(fields)):raise ValueError("duplicate field")
                        reader=csv.DictReader(f,fieldnames=fields,delimiter=sep);break
                if reader is not None:break
            if reader is None:raise ValueError("unknown header")
            for row in reader:
                if None in row or any(v is None for v in row.values()):raise ValueError("malformed trade report")
                counts["sourceRows"]+=1
                if counts["sourceRows"]>5000000:raise ValueError("report row bound")
                key=(row["MifidInstrumentID"].strip(),row["Venue"].strip())
                if key not in expected:continue
                counts["matchedRows"]+=1
                try:
                    p=Decimal(row["MifidPrice"]);q=Decimal(row["MifidQuantity"])
                    t=datetime.fromisoformat(row["TradingDateTime"].replace("Z","+00:00"))
                    pub=datetime.fromisoformat(row["PublicationDateTime"].replace("Z","+00:00"))
                    if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
                    if pub.tzinfo is None:pub=pub.replace(tzinfo=timezone.utc)
                    if pub<t or not p.is_finite() or not q.is_finite() or p<=0 or q<=0 or not re.fullmatch("[A-Z]{3}",row["MifidCurrency"]):raise ValueError("invalid trade")
                except (InvalidOperation,ValueError,TypeError):
                    counts["invalidMatchedRows"]+=1;continue
                uid=row["TradeUniqueIdentifier"].strip()
                if not uid:counts["missingTradeId"]+=1;continue
                k=(key,uid)
                if k in seen:counts["repeatedTradeId"]+=1;continue
                seen.add(k)
                day=t.astimezone(timezone.utc).date().isoformat()
                dates[day]+=1
                identities[key]+=1
                for id_ in expected[key]:matched_dates[(id_,day)]+=1
    if not counts["sourceRows"]:raise ValueError("empty report")
    ids=sorted({x for x,d in matched_dates})
    return {"counts":dict(counts),"matchedListings":len(ids),"matchedListingIds":ids,"eligibleListings":sum(map(len,expected.values())),"matchedTradingDates":dict(dates),"headerFields":fields,"officialCloseEstablished":False,"pricesPublished":0,"rawRowsRetained":0}
def main():
    queue=json.loads((ROOT/"data/price-source-queue-v1.json").read_text())
    groups,total=targets(queue)
    if not groups:raise ValueError("no exact identities")
    results=[]
    for market,expected in sorted(groups.items()):
        url=eur_url(market,"PREVIOUS_TRADING_DAY")
        raw=downloaded(url);stats=parse(raw,expected)
        results.append({"market":market,"url":url,"sourceSha256":hashlib.sha256(raw).hexdigest(),**stats})
    output={"pendingEuronextListings":total,"exactIdentityEligible":sum(sum(map(len,g.values())) for g in groups.values()),"matchedListings":sum(x["matchedListings"] for x in results),"markets":results,"notice":"Coverage of positive report observations only; cancellations, corrections, trading-session rules, off-book flags and official closing prices not established. No price publication or raw trade retention."}
    print("EURONEXT_PRICE_COVERAGE "+json.dumps(output,sort_keys=True))
    if not output["matchedListings"]:raise SystemExit(1)
if __name__=="__main__":main()
