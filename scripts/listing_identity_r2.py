"""Private, content-addressed retention of scoped weekly identity candidates."""
import hashlib,json,os,re
from datetime import date,datetime,timezone
from private_r2_archive import BUCKET,configuration,immutable_put
from exchange_identity import valid_isin
from gleif_isin_lei import valid_lei
from research_coverage import valid_figi, SOURCE
from esma_firds_preflight import DOCS,NAME
from esma_identity_history import RIGHTS
def encode(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def prepare(summary,candidates,targets):
    from listing_identity_batch import VENUES
    group=summary["group"];day=summary["sourceDate"]
    if group not in VENUES or date.fromisoformat(day).isoformat()!=day:raise ValueError("invalid source scope")
    if summary["currentStateEstablished"] is not False or summary["publishedPrices"]!=0 or len(candidates)!=summary["candidateMatches"] or not 0<len(candidates)<=len(targets)<=4000:raise ValueError("invalid counts or claims")
    parts=summary["sourceParts"];numbers=set();totals=set();rows=0
    for part in parts:
        m=NAME.fullmatch(part["name"])
        if not m or m[1]!="FULINS_E" or m[2]!=day.replace("-","") or not re.fullmatch("[a-f0-9]{64}",part["sha256"]) or type(part["rows"]) is not int or part["rows"]<=0:raise ValueError("invalid source part")
        n=int(m[3]);total=int(m[4])
        if n in numbers:raise ValueError("duplicate source part")
        numbers.add(n);totals.add(total);rows+=part["rows"]
    if totals!={len(parts)} or numbers!=set(range(1,len(parts)+1)) or rows!=summary["sourceRows"]:raise ValueError("incomplete source parts")
    ids=set();pairs=set();out=[]
    for r in candidates:
        id_=r["listingId"];pair=(r["isin"],r["mic"])
        if id_ in ids or pair in pairs or targets.get(id_)!=(r["figi"],r["mic"]) or r["mic"] not in VENUES[group] or not valid_isin(r["isin"]) or not valid_figi(r["figi"]) or not valid_lei(r["lei"]) or not re.fullmatch("ES[A-Z]{4}",r["cfi"]) or not re.fullmatch("[A-Z]{3}",r["currency"]):raise ValueError("invalid or ambiguous identity")
        if r.get("status")!="exact_candidate_join" or r.get("reviewRequired") is not True or r.get("pricePublicationAllowed") is not False:raise ValueError("invalid review state")
        ids.add(id_);pairs.add(pair)
        out.append({k:r[k] for k in ("listingId","isin","mic","figi","lei","cfi","currency","status","reviewRequired","pricePublicationAllowed")})
    return {"schemaVersion":1,"group":group,"sourceDate":day,"source":"ESMA FIRDS","sourceUrl":DOCS,"sourceRights":RIGHTS,"mappingSource":SOURCE,"sourceParts":parts,"sourceRows":rows,"candidateMatches":len(out),"currentStateEstablished":False,"publicPublication":False,"records":sorted(out,key=lambda x:x["listingId"])}
def write_verified(client,key,raw):
    state=immutable_put(client,raw,key,{"dataset":"listing-identity-candidates","publicpublication":"false"},"application/json")
    s=client.get_object(Bucket=BUCKET,Key=key)["Body"]
    try:actual=s.read(len(raw)+1)
    finally:s.close()
    if actual!=raw:raise ValueError("readback mismatch")
    return state
def archive(client,summary,candidates,targets,observed_at=None):
    data=prepare(summary,candidates,targets);body=encode(data);digest=sha(body)
    key=f"listing-identity/v1/{data['group']}/{data['sourceDate']}/{digest}.json"
    state=write_verified(client,key,body)
    # Receipt distinguishes the dated regulatory baseline from a later
    # mapping observation. Identical candidate bodies deduplicate across runs.
    stamp=observed_at or datetime.now(timezone.utc).isoformat()
    t=datetime.fromisoformat(stamp)
    if t.tzinfo is None or t.date()<date.fromisoformat(data["sourceDate"]):raise ValueError("invalid mapping observation time")
    receipt=encode({"schemaVersion":1,"objectKey":key,"objectSha256":digest,"sourceDate":data["sourceDate"],"mappingObservedAt":stamp,"candidateMatches":data["candidateMatches"],"currentStateEstablished":False,"publicPublication":False,"readbackVerified":True})
    receipt_key=f"listing-identity/v1/receipts/{sha(receipt)}.json"
    write_verified(client,receipt_key,receipt)
    return {"storageStatus":state,"retainedCandidateRecords":len(candidates),"receiptKey":receipt_key,"readbackVerified":True}
def archive_live(summary,candidates,targets):
    if os.environ.get("STOCKWATCH_IDENTITY_PRIVATE_RETENTION")!="true":raise ValueError("explicit private retention required")
    import boto3
    from botocore.config import Config
    account=configuration(os.environ,smoke_only=True)
    client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
    return archive(client,summary,candidates,targets)
