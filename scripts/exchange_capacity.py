"""Measure report structure and coverage in memory, without storing prices or trade rows."""
import argparse,csv,io,json,sys,zipfile
from collections import Counter
from datetime import datetime,timezone
import delayed_exchange as ex
from exchange_identity import valid_isin

def day(value):
    try:
        d=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        return d.astimezone(timezone.utc).date().isoformat() if d.tzinfo is not None else None
    except (ValueError,AttributeError):return None

def measure(raw):
    if len(raw)>ex.MAX_DOWNLOAD:raise ValueError("Archive exceeds size limit")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>ex.MAX_EXPANDED:raise ValueError("Unexpected report")
        entry=files[0]
        with z.open(entry) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
            for _ in range(4):
                line=f.readline()
                for sep in (",",";","\t"):
                    header=next(csv.reader([line],delimiter=sep))
                    if ex.REQUIRED.issubset(header):break
                else:continue
                break
            else:raise ValueError("Unknown report schema")
            if len(header)!=len(set(header)):raise ValueError("Duplicate columns")
            rows=malformed=invalid_identity=invalid_time=0
            securities=set();venues=set();currencies=set();days=set();pubdays=set()
            for row in csv.DictReader(f,fieldnames=header,delimiter=sep):
                rows+=1
                if None in row or any(v is None for v in row.values()):
                    malformed+=1;continue
                isin=row["MifidInstrumentID"].strip()
                mic=row["Venue"].strip()
                if valid_isin(isin):
                    securities.add(isin)
                else:invalid_identity+=1
                if mic:venues.add(mic)
                currency=row["MifidCurrency"].strip()
                if currency:currencies.add(currency)
                t=day(row["TradingDateTime"]);p=day(row["PublicationDateTime"])
                if t:days.add(t)
                if p:pubdays.add(p)
                if not t or not p:invalid_time+=1
            return {"zipBytes":len(raw),"csvBytes":entry.file_size,"columns":len(header),
                    "reportRows":rows,"malformedRows":malformed,"invalidIdentityRows":invalid_identity,
                    "invalidTimestampRows":invalid_time,"distinctValidISINs":len(securities),
                    "distinctVenueCodes":len(venues),"distinctCurrencies":len(currencies),
                    "tradeUTCDateMin":min(days,default=None),"tradeUTCDateMax":max(days,default=None),
                    "publicationUTCDateMin":min(pubdays,default=None),"publicationUTCDateMax":max(pubdays,default=None),
                    "schemaValidated":True,"pricesStored":False,"rawReportStored":False,
                    "completeSessionVerified":False,"uniqueExecutedTradesVerified":False}

def audit(markets,fetch=ex.downloaded):
    out=[]
    for market in markets:
        try:
            info=measure(fetch(ex.eur_url(market,"PREVIOUS_TRADING_DAY")))
            out.append({"market":market,"status":"measured",**info})
        except ex.HTTPError as e:
            out.append({"market":market,"status":"http_error","httpStatus":e.code})
            if e.code in (401,403,429):break
        except Exception as e:
            out.append({"market":market,"status":"unavailable","errorType":type(e).__name__})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--markets",nargs="+",choices=ex.MARKETS,default=list(ex.MARKETS))
    a=p.parse_args()
    results=audit(tuple(dict.fromkeys(a.markets)))
    for r in results:print("CAPACITY "+json.dumps(r,sort_keys=True),flush=True)
    return 0 if any(r["status"]=="measured" for r in results) else 1
if __name__=="__main__":sys.exit(main())
