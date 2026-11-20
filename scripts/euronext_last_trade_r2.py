"""Private R2-only, content-addressed Euronext last-trade observations.

Never expose derived prices in public CI logs, Git, a public bucket or an API.
Requires separately reviewed internal retention; public display/sale remains OFF.
"""
from __future__ import annotations
import hashlib,json,os,re
from collections import defaultdict
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from private_r2_archive import BUCKET,configuration,immutable_put
from euronext_price_coverage import MARKETS
from private_trade_bars import ts,ZONES
from zoneinfo import ZoneInfo

TERMS="https://marketdata.euronext.com/data-reporting-service/trades-file"
CLASSIFICATION="observed_central_order_book_last_trade_not_official_close"
def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")
def digest(value):return hashlib.sha256(value).hexdigest()
def checked(quotes,markets):
    lookup={m["market"]:m for m in markets}
    if not lookup or len(lookup)!=len(markets) or not set(lookup)<=set(MARKETS.values()):
        raise ValueError("Invalid exchange source scope")
    if not 0<len(quotes)<=500:raise ValueError("No bounded derived observations")
    groups=defaultdict(list);used=set()
    for q in quotes:
        pair=(q.get("listingId"),q.get("mic"),q.get("date"))
        if pair in used or q.get("mic") not in MARKETS or MARKETS[q["mic"]] not in lookup:
            raise ValueError("Duplicate or unmatched quote")
        used.add(pair)
        day=date.fromisoformat(q["date"])
        if day>datetime.now(timezone.utc).date():raise ValueError("Future session")
        if q.get("classification")!=CLASSIFICATION or q.get("officialClose") is not False or q.get("publicPublicationAllowed") is not False or q.get("historicalRetentionApproved") is not False:
            raise ValueError("Public data / rights claim prohibited")
        if not re.fullmatch(r"[A-Z]{3}",q.get("currency","")) or type(q.get("observedEligibleTrades")) is not int or q["observedEligibleTrades"]<1:
            raise ValueError("Invalid quote metadata")
        try:price=Decimal(str(q["lastTradePrice"]))
        except (InvalidOperation,ValueError,TypeError):raise ValueError("Invalid price") from None
        if not price.is_finite() or price<=0 or not re.fullmatch(r"\d{1,12}(\.\d{1,12})?",str(price)):
            raise ValueError("Invalid price precision")
        if ts(q["lastTradeAt"]).astimezone(ZoneInfo(ZONES[q["mic"]])).date()!=day:raise ValueError("Inconsistent venue-local session date")
        groups[MARKETS[q["mic"]]].append(q)
    for market,meta in lookup.items():
        if not re.fullmatch(r"[0-9a-f]{64}",meta.get("sourceSha256","")) or type(meta.get("eligibleListings")) is not int:
            raise ValueError("Invalid source provenance")
        if market not in groups:raise ValueError("Missing source data for a scope")
    return groups

def archive(client,quotes,markets,observed_at=None):
    groups=checked(quotes,markets)
    stamp=observed_at or datetime.now(timezone.utc).isoformat()
    if ts(stamp)>datetime.now(timezone.utc).astimezone(timezone.utc).replace(microsecond=999999):
        raise ValueError("Future archive timestamp")
    out=[]
    for market in sorted(groups):
        meta=next(x for x in markets if x["market"]==market)
        data={"schemaVersion":1,"source":"Euronext","sourceTerms":TERMS,
              "sourceSha256":meta["sourceSha256"],"sourceWindow":"PREVIOUS_TRADING_DAY",
              "market":market,
              "classification":CLASSIFICATION,"officialClose":False,
              "publicPublicationAllowed":False,"commercialExportAllowed":False,
              "privateRetentionReviewed":True,
              "records":sorted(groups[market],key=lambda q:(q["date"],q["listingId"]))}
        body=encoded(data);sha=digest(body)
        key=f"euronext-last-trade/v1/{market}/{sha}.json"
        state=immutable_put(client,body,key,{"dataset":"euronext-last-trade","publicpublication":"false"},"application/json")
        stream=client.get_object(Bucket=BUCKET,Key=key)["Body"]
        try:readback=stream.read(len(body)+1)
        finally:stream.close()
        if readback!=body:raise ValueError("Private archive readback mismatch")
        receipt=encoded({"schemaVersion":1,"market":market,"objectKey":key,"objectSha256":sha,"retrievedAt":stamp,"privateRetentionReviewed":True,"publicPublication":False,"readbackVerified":True})
        receiptKey=f"euronext-last-trade/v1/receipts/{digest(receipt)}.json"
        immutable_put(client,receipt,receiptKey,{"dataset":"euronext-last-trade-receipt","publicpublication":"false"},"application/json")
        out.append({"market":market,"storageStatus":state,"retainedObservations":len(groups[market]),"readbackVerified":True})
    return {"markets":out,"retainedObservations":sum(x["retainedObservations"] for x in out),
            "readbackVerified":all(x["readbackVerified"] for x in out),
            "publicPublication":False}

def archive_live(quotes,markets):
    if os.environ.get("STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED")!="true":
        raise ValueError("Explicit internal derived retention scope required")
    import boto3
    from botocore.config import Config
    account=configuration(os.environ)
    client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
          region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],
          aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],
          config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
    return archive(client,quotes,markets)
