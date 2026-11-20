"""Retain bounded exact ESMA revision evidence in the existing private archive."""
import hashlib,json,os,re
from datetime import date,timedelta
from esma_identity_history import RIGHTS,encode
from esma_firds_preflight import DOCS
from private_r2_archive import BUCKET,configuration,immutable_put
from esma_revision_evidence import ROOT

def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify_date(s):
    if not isinstance(s,str) or date.fromisoformat(s).isoformat()!=s:raise ValueError("invalid date")
    return date.fromisoformat(s)
def prepare(root):
    raw=(root/"index.json").read_bytes()
    if len(raw)>100000:raise ValueError("index bound")
    index=json.loads(raw)
    if index["status"]!="ok" or any(index[k] is not False for k in ("currentStateEstablished","replayComplete","consolidatedCancellationReconciled")):raise ValueError("invalid evidence claim")
    start=verify_date(index["baselineDate"]);end=verify_date(index["throughDate"])
    days=index["days"]
    if not 1<=len(days)<=8 or (end-start).days!=len(days):raise ValueError("incomplete window")
    objects=[];matched=0;source_actions=0;action_counts={}
    for offset,entry in enumerate(days,1):
        day=(start+timedelta(days=offset)).isoformat()
        digest=entry["sha256"]
        if entry["date"]!=day or not re.fullmatch("[a-f0-9]{64}",digest):raise ValueError("invalid day")
        name=day+"-"+digest+".json"
        if entry["path"]!="data/esma-delta-history/"+name:raise ValueError("invalid path")
        p=root/name
        if p.is_symlink() or p.stat().st_size>32_000_000:raise ValueError("payload bound")
        body=p.read_bytes()
        if sha(body)!=digest:raise ValueError("payload checksum")
        d=json.loads(body)
        if d["schemaVersion"]!=1 or d["source"]!="ESMA FIRDS" or d["sourceUrl"]!=DOCS or d["sourceRights"]!=RIGHTS or d["publicationFileDate"]!=day:raise ValueError("invalid source evidence")
        records=d["records"];parts=d["parts"];counts=d["sourceActionCounts"]
        if not isinstance(records,list) or not isinstance(parts,list) or not 1<=len(parts)<=16:raise ValueError("invalid evidence layout")
        if any(type(v) is not int or v<0 for v in counts.values()):raise ValueError("invalid action count")
        n=sum(counts.values())
        if n<=0 or len(records)!=d["matchedEvents"] or len(records)!=entry["matchedEvents"] or n!=entry["sourceActions"] or len(parts)!=entry["sourceParts"]:raise ValueError("coverage mismatch")
        matched+=len(records);source_actions+=n
        for k,v in counts.items():action_counts[k]=action_counts.get(k,0)+v
        objects.append((f"esma-revisions/v1/days/{day}/{digest}.json",body))
    if matched!=index["matchedEvents"] or action_counts!=index["sourceActionCounts"]:raise ValueError("aggregate mismatch")
    receipt=encode({"schemaVersion":1,"source":"ESMA FIRDS","sourceRights":RIGHTS,"indexSha256":sha(raw),"baselineDate":index["baselineDate"],"throughDate":index["throughDate"],"sourceActionsScanned":source_actions,"matchedEventsRetained":matched,"currentStateEstablished":False,"publicPublication":False,"objects":[{"key":k,"sha256":sha(b),"bytes":len(b)} for k,b in objects]})
    return objects,(f"esma-revisions/v1/receipts/{sha(receipt)}.json",receipt),matched,source_actions
def put_verified(client,key,raw):
    state=immutable_put(client,raw,key,{"dataset":"esma-revisions","publicpublication":"false"},"application/json")
    result=client.get_object(Bucket=BUCKET,Key=key)["Body"]
    try:body=result.read(len(raw)+1)
    finally:result.close()
    if sha(body)!=sha(raw) or len(body)!=len(raw):raise ValueError("readback mismatch")
    return state
def archive(client,root):
    objects,receipt,matched,scanned=prepare(root)
    states=[put_verified(client,k,b) for k,b in objects]
    put_verified(client,*receipt)
    return {"days":len(objects),"matchedEventsRetained":matched,"sourceActionsScanned":scanned,"created":states.count("created"),"alreadyPresent":states.count("already_present"),"receiptKey":receipt[0],"readbackVerified":True,"currentStateEstablished":False,"publicPublication":False}
def main():
    if os.environ.get("STOCKWATCH_ESMA_PRIVATE_RETENTION")!="true":raise ValueError("retention not enabled")
    account=configuration(os.environ,smoke_only=True)
    import boto3
    from botocore.config import Config
    client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
    print("ESMA_REVISION_R2_VERIFIED "+json.dumps(archive(client,ROOT/"data/esma-delta-history"),sort_keys=True))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("ESMA_REVISION_R2_FAILED "+type(exc).__name__)
        raise SystemExit(1) from None
