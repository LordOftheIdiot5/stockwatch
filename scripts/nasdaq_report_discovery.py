"""Bounded Nasdaq Nordic report availability discovery. No trade downloads."""
import json,re
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,unquote
from collections import Counter
from delayed_exchange import NAS,downloaded,nasdaq_links
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POLICY="https://www.nasdaq.com/market-regulation/nordic/mifid-ii"
def inspect(raw,now):
    timestamps=set()
    links=nasdaq_links(raw)
    for u in links:
        p=urlsplit(u)
        if p.hostname!="tradereports.nasdaq.com" or p.scheme!="https" or p.username or p.password:continue
        m=re.search(r"NordicEquity-posttrade-(\d{4}-\d{2}-\d{2}T\d{4})(?!\d)",unquote(p.path+"?"+p.query),re.I)
        if not m:continue
        try:stamp=datetime.strptime(m[1],"%Y-%m-%dT%H%M")
        except ValueError:continue
        # Filename timezone not established. Count dates, not presumed UTC times.
        if stamp.date()>(now+timedelta(days=1)).date():continue
        timestamps.add(stamp)
    counts=Counter(x.date().isoformat() for x in timestamps)
    latest=max(timestamps,default=None)
    dates=sorted(counts)
    recent=bool(latest and (now.date()-latest.date()).days<=2)
    return {"source":NAS,"policy":POLICY,"linksDiscovered":len(links),"datedMinuteFiles":len(timestamps),"fileDates":dict(sorted(counts.items())),"latestFilename":latest.isoformat(timespec="minutes") if latest else None,"recentFileDate":recent,"status":"recent_links" if recent else "stale_or_missing_links","filenameTimezoneVerified":False,"dailyCompletenessVerified":False,"tradeFilesDownloaded":0,"pricesPublished":0}
def main():
    queue=json.loads((ROOT/"data/price-source-queue-v1.json").read_text())["queues"]["nasdaq_nordic"]
    report=inspect(downloaded(NAS,8*1024*1024),datetime.now(timezone.utc))
    report["pendingListings"]=queue["missing"]
    report["exactISINMIC"]=sum(r.get("identityStatus")=="isin_and_mic" for r in queue["records"])
    print("NASDAQ_REPORT_DISCOVERY "+json.dumps(report,sort_keys=True))
    if not report["recentFileDate"]:raise SystemExit(1)
if __name__=="__main__":main()
