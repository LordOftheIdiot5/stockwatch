"""Official delayed exchange data: private research only, never publish trade rows."""
import argparse,csv,hashlib,io,json,os,re,sys,zipfile
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
EUR="https://marketdata.euronext.com/data-reporting-service/trades-file"
NAS="https://tradereports.nasdaq.com/shares/trade-reports/post-trade"
NAS_BALTIC="https://tradereports.nasdaq.com/baltic-trade-reports/equity/post-trade"
NAS_PORTALS={"nordic":NAS,"baltic":NAS_BALTIC}
NAS_PREFIX={"nordic":"nordicequity-posttrade","baltic":"balticequity-posttrade"}
MAX_DOWNLOAD=64*1024*1024
MAX_EXPANDED=512*1024*1024
MARKETS=("OSL","PAR","AMS","BRU","DUB","LIS","MIL")
REQUIRED={"TradingDateTime","PublicationDateTime","MifidInstrumentID","MifidPrice","MifidQuantity","MifidCurrency","Venue","TradeUniqueIdentifier"}
def downloaded(url,limit=MAX_DOWNLOAD,timeout=120):
    req=Request(url,headers={"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev)","Accept":"*/*"})
    with urlopen(req,timeout=timeout) as r:
        if urlparse(r.geturl()).scheme!="https" or urlparse(r.geturl()).hostname!=urlparse(url).hostname:
            raise ValueError("Unexpected source redirect")
        data=r.read(limit+1)
    if len(data)>limit:raise ValueError("Download exceeds configured bound")
    return data
def eur_url(market,window):
    if market not in MARKETS or window not in ("PREVIOUS_TRADING_DAY","CURRENT_TRADING_DAY","LAST_HOUR","LAST_15_MINUTES"):
        raise ValueError("Unsupported market/window")
    return EUR+"/download/EQUITIES/"+window+"/"+market
def csv_schema(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>MAX_EXPANDED:raise ValueError("Unexpected trade archive")
        with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
            for _ in range(4):
                line=f.readline()
                if not line:break
                for sep in (",",";","\t"):
                    fields=next(csv.reader([line],delimiter=sep))
                    if REQUIRED.issubset(set(fields)):
                        return {"format":"zip/csv","schemaValidated":True}
        raise ValueError("Unrecognized Euronext trade schema")
class Links(HTMLParser):
    def __init__(self,region="nordic"):
        super().__init__()
        self.region=region
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag!="a":return
        href=dict(attrs).get("href") or ""
        u=urljoin(NAS_PORTALS[self.region],href)
        p=urlparse(u)
        if (p.scheme=="https" and p.netloc=="tradereports.nasdaq.com"
                and not p.fragment and NAS_PREFIX[self.region] in p.path.lower()
                and re.search(r"posttrade-\d{4}-\d{2}-\d{2}t\d{4}",p.path,re.I)):
            self.links.append(u)
def nasdaq_links(raw,region="nordic"):
    p=Links(region);p.feed(raw.decode("utf-8",errors="replace"))
    return sorted(set(p.links))
def nasdaq_discovery(fetch=downloaded):
    regions={}
    for region,url in NAS_PORTALS.items():
        try:
            raw=downloaded(url,8*1024*1024,timeout=30) if fetch is downloaded else fetch(url,8*1024*1024)
            links=nasdaq_links(raw,region)
            regions[region]={"status":"links_observed" if links else "no_recognized_report_links",
                             "discoveredLinkCount":len(links)}
        except HTTPError as e:
            regions[region]={"status":"http_error","httpStatus":e.code,"discoveredLinkCount":0}
        except Exception as e:
            regions[region]={"status":"not_validated","errorType":type(e).__name__,"discoveredLinkCount":0}
    count=sum(x["discoveredLinkCount"] for x in regions.values())
    return {"status":"discovery_only","downloadLinksFound":bool(count),
            "discoveredLinkCount":count,"regions":regions,"tradeDownloadEnabled":False}
def private_save(raw,dest,provider):
    dest=Path(dest).expanduser().resolve()
    if dest==ROOT or ROOT in dest.parents:raise ValueError("Private archive must be outside repository")
    dest=dest/provider;dest.mkdir(parents=True,exist_ok=True)
    name=hashlib.sha256(raw).hexdigest()+".zip"
    target=dest/name
    if not target.exists():
        tmp=target.with_suffix(".tmp");tmp.write_bytes(raw);tmp.replace(target)
    return name
def probe(market="OSL",window="PREVIOUS_TRADING_DAY",archive=None,fetch=downloaded):
    if archive and os.environ.get("STOCKWATCH_R2_RETENTION_APPROVED")!="true":
        raise ValueError("Persistent local archive requires reviewed retention approval")
    result={"checkedAt":datetime.now(timezone.utc).isoformat(),"euronext":{"status":"not_checked"},"nasdaq":{"status":"not_checked"},"publicPublication":False}
    try:
        raw=fetch(eur_url(market,window))
        info=csv_schema(raw)
        if archive:private_save(raw,archive,"euronext")
        result["euronext"]={"status":"schema_validated","market":market,**info,"privateArchive":bool(archive)}
    except HTTPError as e:result["euronext"]={"status":"http_error","httpStatus":e.code}
    except Exception as e:result["euronext"]={"status":"not_validated","errorType":type(e).__name__}
    result["nasdaq"]=nasdaq_discovery(fetch)
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",choices=MARKETS,default="OSL")
    p.add_argument("--window",default="PREVIOUS_TRADING_DAY")
    p.add_argument("--private-archive",type=Path,help="Optional persistent directory outside repository; Euronext only")
    a=p.parse_args()
    status=probe(a.market,a.window,a.private_archive)
    print(json.dumps(status))
    return 0 if status["euronext"]["status"]=="schema_validated" else 1
if __name__=="__main__":sys.exit(main())
