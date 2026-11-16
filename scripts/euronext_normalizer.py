"""Normalize reviewed Euronext report profiles into private research snapshots.

No default MMT flag interpretation. Unknown flags, revisions or ambiguous trade
IDs block the affected instrument/session. Never derive an official close.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,zipfile,sqlite3
from collections import defaultdict
from pathlib import Path
from datetime import timezone
from zoneinfo import ZoneInfo
import delayed_exchange as ex
import private_trade_bars as ledger
from exchange_identity import valid_isin, universe

def rows(raw):
    if len(raw)>ex.MAX_DOWNLOAD:raise ValueError("Archive too large")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[f for f in z.infolist() if not f.is_dir() and f.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>ex.MAX_EXPANDED:raise ValueError("Unexpected archive")
        with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
            for _ in range(4):
                line=f.readline()
                for sep in (",",";","\t"):
                    h=next(csv.reader([line],delimiter=sep))
                    if ex.REQUIRED.issubset(h):
                        if len(h)!=len(set(h)):raise ValueError("Duplicate columns")
                        yield h
                        for r in csv.DictReader(f,fieldnames=h,delimiter=sep):
                            if None in r or any(v is None for v in r.values()):raise ValueError("Malformed row")
                            yield r
                        return
            raise ValueError("Unrecognized report")
def normalize(raw,policy,approved):
    if policy.get("reviewed") is not True or not policy.get("specificationReference"):
        raise ValueError("Reviewed report profile required")
    flags=policy.get("flagColumns")
    if not isinstance(flags,list) or not flags or len(set(flags))!=len(flags):raise ValueError("Flag columns required")
    allowed={tuple(x) for x in policy.get("eligibleFlagTuples",[])}
    excluded={tuple(x) for x in policy.get("excludedFlagTuples",[])}
    if not allowed or allowed&excluded or any(len(x)!=len(flags) for x in allowed|excluded):raise ValueError("Invalid flag policy")
    it=iter(rows(raw));head=next(it)
    if set(head)!=set(policy.get("expectedColumns",[])) or not set(flags).issubset(head):raise ValueError("Reviewed schema mismatch")
    groups=defaultdict(dict);blocked=set()
    for r in it:
        mic=r["Venue"].strip();isin=r["MifidInstrumentID"].strip()
        m=approved.get((mic,isin))
        if not m:continue
        t=ledger.ts(r["TradingDateTime"].strip());p=ledger.ts(r["PublicationDateTime"].strip())
        day=t.astimezone(ZoneInfo(ledger.ZONES[mic])).date().isoformat()
        group=(mic,isin,day)
        f=tuple(r[k].strip() for k in flags)
        # Only explicitly reviewed eligible/excluded ordinary trades can pass.
        # Unknown/correction flags quarantine the entire session; no guessing.
        if f not in allowed and f not in excluded:
            blocked.add(group);continue
        if r["MifidCurrency"].strip()!=m["currency"]:
            blocked.add(group);continue
        e=dict(mic=mic,isin=isin,listingId=m["listingId"],sessionDate=day,
            tradeId=r["TradeUniqueIdentifier"].strip(),revision=0,action="upsert",
            currency=m["currency"],eligible=f in allowed,tradeTime=t.isoformat(),
            eventTime=p.isoformat(),price=r["MifidPrice"].strip(),quantity=r["MifidQuantity"].strip())
        try:e=ledger.validate(e,{(mic,isin):m["listingId"]})
        except (ValueError,KeyError,TypeError):blocked.add(group);continue
        old=groups[group].get(e["tradeId"])
        if old is not None and old!=e:blocked.add(group)
        groups[group][e["tradeId"]]=e
    events=[e for k,g in groups.items() if k not in blocked for e in g.values()]
    return events,blocked
def snapshot(raw,policy,approved):
    events,blocked=normalize(raw,policy,approved)
    with sqlite3.connect(":memory:") as db:
        ledger.ingest(db,events,{k:v["listingId"] for k,v in approved.items()})
        result=ledger.bars(db)
    return {"source":"Euronext","archiveSHA256":hashlib.sha256(raw).hexdigest(),
            "notice":"Single-report observed bars; unverified completeness, not official close. No public publication.",
            "bars":result,"quarantinedSessions":[list(x) for x in sorted(blocked)]}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("archive","policy","mappings","output"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    source,profile,mapping,out=[ledger.private_path(x) for x in (a.archive,a.policy,a.mappings,a.output)]
    if len({source,profile,mapping,out})!=4:raise ValueError("Distinct private paths required")
    manifest=json.loads(mapping.read_text())
    if manifest.get("internalRetentionReviewed") is not True or manifest.get("mappingReviewed") is not True:raise ValueError("Retention and mappings require review")
    known={r["id"]:r for r in universe()};approved={}
    for r in manifest["mappings"]:
        k=(r["mic"],r["isin"]);v=known.get(r["listingId"])
        if not v or v["mic"]!=k[0] or not valid_isin(k[1]) or (v.get("isin") and v["isin"]!=k[1]) or not v.get("figi") or v["figi"]!=r.get("figi") or k in approved or any(x["listingId"]==r["listingId"] for x in approved.values()):
            raise ValueError("Invalid exact reviewed mapping")
        approved[k]=r
    result=snapshot(source.read_bytes(),json.loads(profile.read_text()),approved)
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix(".tmp");tmp.write_text(json.dumps(result,indent=2)+"\n");tmp.replace(out)
    print("Private snapshot processed; public publication disabled.")
if __name__=="__main__":main()
