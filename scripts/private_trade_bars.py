"""Private trade-ledger and derived OHLCV engine for reviewed normalized events.

Not a raw Euronext MMT parser. The caller must review venue-specific eligible
trades, correction semantics, session calendar, currencies and retention rights.
No official closing price, completeness or public redistribution is implied.
"""
from __future__ import annotations
import argparse,json,sqlite3
from collections import defaultdict
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
from exchange_identity import valid_isin
ROOT=Path(__file__).resolve().parents[1]
ZONES={"XOSL":"Europe/Oslo","XPAR":"Europe/Paris","XAMS":"Europe/Amsterdam","XBRU":"Europe/Brussels","XDUB":"Europe/Dublin","XLIS":"Europe/Lisbon","XMIL":"Europe/Rome","XSTO":"Europe/Stockholm","XCSE":"Europe/Copenhagen","XHEL":"Europe/Helsinki"}
def private_path(path):
    p=Path(path).expanduser().resolve()
    if p==ROOT or ROOT in p.parents:raise ValueError("All ledger files must remain outside repository")
    return p
def ts(v):
    d=datetime.fromisoformat(v.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timestamp must include timezone")
    return d.astimezone(timezone.utc)
def number(v):
    try:d=Decimal(str(v))
    except InvalidOperation:raise ValueError("Invalid decimal")
    if not d.is_finite() or d<=0:raise ValueError("Expected positive finite decimal")
    return d
def validate(e,approved):
    mic=e["mic"];isin=e["isin"];day=date.fromisoformat(e["sessionDate"])
    if not valid_isin(isin) or mic not in ZONES:raise ValueError("Unknown venue or ISIN")
    if approved.get((mic,isin))!=e["listingId"]:raise ValueError("Mapping not reviewed")
    trading=ts(e["tradeTime"]);published=ts(e["eventTime"])
    if trading.astimezone(ZoneInfo(ZONES[mic])).date()!=day or published<trading:raise ValueError("Session or event timestamp mismatch")
    if day>datetime.now(timezone.utc).date():raise ValueError("Future session")
    if not isinstance(e["tradeId"],str) or not e["tradeId"].strip() or len(e["tradeId"])>200:raise ValueError("Invalid trade id")
    if type(e["revision"]) is not int or e["revision"]<0:raise ValueError("Invalid event revision")
    if e["action"] not in ("upsert","cancel"):raise ValueError("Unknown action")
    if not isinstance(e["currency"],str) or len(e["currency"])!=3 or not e["currency"].isascii() or not e["currency"].isalpha() or not e["currency"].isupper():raise ValueError("Invalid currency")
    if type(e["eligible"]) is not bool:raise ValueError("Explicit reviewed eligibility required")
    row={k:e[k] for k in ("mic","isin","listingId","sessionDate","tradeId","revision","action","currency","eligible")}
    row.update(tradeTime=trading.isoformat(),eventTime=published.isoformat())
    if e["action"]=="upsert":row.update(price=str(number(e["price"])),quantity=str(number(e["quantity"])))
    return row
def setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS events(
      mic TEXT, isin TEXT, session TEXT, trade TEXT, revision INTEGER, body TEXT,
      PRIMARY KEY(mic,isin,session,trade,revision))""")
def ingest(db,events,approved):
    setup(db)
    with db:
        for raw in events:
            e=validate(raw,approved)
            k=(e["mic"],e["isin"],e["sessionDate"],e["tradeId"],e["revision"])
            payload=json.dumps(e,sort_keys=True,separators=(",",":"))
            old=db.execute("SELECT body FROM events WHERE mic=? AND isin=? AND session=? AND trade=? AND revision=?",k).fetchone()
            if old and old[0]!=payload:raise ValueError("Conflicting event revision")
            if not old:db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",(*k,payload))
def bars(db):
    setup(db)
    rows=db.execute("""SELECT e.body FROM events e JOIN
      (SELECT mic,isin,session,trade,MAX(revision) revision FROM events GROUP BY mic,isin,session,trade) x
      USING(mic,isin,session,trade,revision)""")
    groups=defaultdict(list)
    for (body,) in rows:
        e=json.loads(body)
        if e["action"]=="cancel" or not e["eligible"]:continue
        groups[(e["listingId"],e["mic"],e["isin"],e["sessionDate"])].append(e)
    out=[]
    for (id,mic,isin,day),items in sorted(groups.items()):
        if len({e["currency"] for e in items})!=1:raise ValueError("Mixed currency in session")
        items.sort(key=lambda e:(ts(e["tradeTime"]),e["tradeId"]))
        prices=[number(e["price"]) for e in items]
        # Equal timestamps lack exchange sequence; no authoritative open/close.
        if (len({e["price"] for e in items if e["tradeTime"]==items[0]["tradeTime"]})>1 or
            len({e["price"] for e in items if e["tradeTime"]==items[-1]["tradeTime"]})>1):
            opening=closing=None
        else:opening=str(prices[0]);closing=str(prices[-1])
        out.append({"listingId":id,"mic":mic,"isin":isin,"date":day,"currency":items[0]["currency"],
            "open":opening,"high":str(max(prices)),"low":str(min(prices)),"close":closing,
            "volume":str(sum(number(e["quantity"]) for e in items)),"observedTrades":len(items),
            "coverage":"partial_or_unverified","officialClose":False,"publicPublicationAllowed":False})
    return out
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events",type=Path,required=True,help="Reviewed normalized JSONL, not raw report")
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--database",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();files=[private_path(x) for x in (a.events,a.manifest,a.database,a.output)]
    ev,manifest,dest,out=files
    m=json.loads(manifest.read_text())
    if any(m.get(k) is not True for k in ("internalRetentionReviewed","normalizedEventsReviewed","mappingReviewed")):raise ValueError("Explicit reviewed internal-use rights and event semantics required")
    approved={}
    for r in m["mappings"]:
        k=(r["mic"],r["isin"])
        if k in approved or r["listingId"] in approved.values():raise ValueError("Ambiguous manifest mapping")
        approved[k]=r["listingId"]
    dest.parent.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(dest) as db,ev.open(encoding="utf-8") as f:
        ingest(db,(json.loads(line) for line in f if line.strip()),approved)
        result=bars(db)
    temp=out.with_suffix(".tmp");temp.write_text(json.dumps({"notice":"Private observed eligible trade bars; not official closes or complete sessions.","bars":result},indent=2)+"\n");temp.replace(out)
    print("Private ledger processed; public publication disabled.")
if __name__=="__main__":main()
