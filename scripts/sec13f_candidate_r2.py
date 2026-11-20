"""Private SEC 13F candidate evidence; no established historical ownership."""
import hashlib,json,os,re
from collections import defaultdict
from datetime import datetime
from private_r2_archive import BUCKET,configuration,immutable_put
from sec13f_source import URL,SOURCE

NOTICE="As-filed candidates using a contemporary FIGI mapping; historical identity, amendments and manager overlap unresolved. No holdings totals or public redistribution."
FIELDS={"listingId","accession","sourceRowKey","managerCIK","filingDate","reportPeriod","form","amendmentType","sourceFIGI","matchLevels","reportedValue","valueUnit","reportedQuantity","quantityType","putCall","otherManagerReferencePresent","classification","historicalIdentityVerified"}
def encode(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def prepare(records,summary,meta,mapped_at):
    if (meta["url"]!=URL or not re.fullmatch("[a-f0-9]{64}",meta["sha256"])
        or type(meta["bytes"]) is not int or not 0<meta["bytes"]<=200*1024**2):raise ValueError("invalid source")
    dt=datetime.fromisoformat(mapped_at)
    if dt.utcoffset() is None:raise ValueError("missing mapping offset")
    if not 1<=len(records)<=100000 or len(records)!=summary["counts"].get("matchedRows") or summary["verifiedHoldings"]!=0:raise ValueError("coverage mismatch")
    grouped=defaultdict(list);seen=set()
    for r in records:
        if set(r)!=FIELDS or r["historicalIdentityVerified"] is not False:raise ValueError("invalid evidence fields")
        listing=r["listingId"]
        if not re.fullmatch(r"X(?:NAS|NYS|ASE):[A-Z0-9.\-]{1,24}",listing):raise ValueError("invalid listing")
        key=(r["accession"],r["sourceRowKey"])
        if key in seen or not all(key):raise ValueError("duplicate or missing row key")
        seen.add(key)
        if not r["matchLevels"] or not set(r["matchLevels"])<={"figi","compositeFIGI","shareClassFIGI"}:raise ValueError("invalid match levels")
        grouped[listing].append(r)
    if len(grouped)!=summary["matchedListings"] or len(grouped)>50:raise ValueError("listing coverage")
    if {k:len(v) for k,v in grouped.items()}!={k:v["matchedRows"] for k,v in summary["listingCounts"].items()}:raise ValueError("listing count mismatch")
    objects=[]
    for listing,rows in sorted(grouped.items()):
        raw=encode({"schemaVersion":1,"source":SOURCE,"sourceArchive":meta,"mappingObservedAt":mapped_at,"listingId":listing,"records":sorted(rows,key=lambda r:(r["accession"],r["sourceRowKey"])),"notice":NOTICE,"publicPublication":False})
        if len(raw)>32_000_000:raise ValueError("listing payload bound")
        objects.append((f"sec13f-candidates/v1/listings/{listing}/{sha(raw)}.json",raw))
    receipt=encode({"schemaVersion":1,"sourceArchive":meta,"mappingObservedAt":mapped_at,"candidateRows":len(records),"verifiedHoldings":0,"objects":[{"key":k,"sha256":sha(b),"bytes":len(b)} for k,b in objects],"notice":NOTICE,"publicPublication":False,"status":"readback_verified"})
    return objects,(f"sec13f-candidates/v1/receipts/{sha(receipt)}.json",receipt)

def put_verified(client,key,raw):
    state=immutable_put(client,raw,key,{"dataset":"sec13f-candidates","publicpublication":"false"},"application/json")
    stream=client.get_object(Bucket=BUCKET,Key=key)["Body"]
    try:actual=stream.read(len(raw)+1)
    finally:stream.close()
    if len(actual)!=len(raw) or sha(actual)!=sha(raw):raise ValueError("R2 readback mismatch")
    return state

def archive(client,records,summary,meta,mapped_at):
    objects,receipt=prepare(records,summary,meta,mapped_at)
    states=[put_verified(client,k,b) for k,b in objects]
    put_verified(client,*receipt)
    return {"candidateRows":len(records),"listings":len(objects),"created":states.count("created"),"alreadyPresent":states.count("already_present"),"receiptKey":receipt[0],"readbackVerified":True,"verifiedHoldings":0,"publicPublication":False}

def archive_live(records,summary,meta,mapped_at):
    if os.environ.get("STOCKWATCH_13F_PRIVATE_RETENTION")!="true":raise ValueError("private retention not enabled")
    account=configuration(os.environ,smoke_only=True)
    import boto3
    from botocore.config import Config
    client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
    try:
        result=archive(client,records,summary,meta,mapped_at)
    except Exception as exc:
        print("SEC_13F_R2_FAILED "+type(exc).__name__)
        raise SystemExit(1) from None
    print("SEC_13F_R2_VERIFIED "+json.dumps(result,sort_keys=True))
