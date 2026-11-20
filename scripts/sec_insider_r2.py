"""Private retention of validated SEC insider evidence, with byte readback."""
import hashlib,json,os,re
from pathlib import Path
from private_r2_archive import BUCKET,configuration,immutable_put
from sec_insider_source import URL,SOURCE
from sec_insider_evidence import ROOT,encode

def sha(b):return hashlib.sha256(b).hexdigest()

def prepare(root):
    manifest=(root/"index.json").read_bytes()
    if len(manifest)>100_000:raise ValueError("manifest bound")
    index=json.loads(manifest)
    meta=index["archive"]
    if (meta["url"]!=URL or not re.fullmatch("[a-f0-9]{64}",meta["sha256"])
        or type(meta["bytes"]) is not int or not 0<meta["bytes"]<=64*1024**2
        or index["publishedTransactions"]!=0):raise ValueError("source manifest")
    refs=index["files"]
    if not 1<=len(refs)<=50:raise ValueError("issuer bound")
    objects=[];seen=set();count=0;nonempty=0
    for ref in refs:
        cik=ref["issuerCIK"];digest=ref["sha256"]
        if not re.fullmatch("[0-9]{10}",cik) or not re.fullmatch("[a-f0-9]{64}",digest) or cik in seen:raise ValueError("issuer reference")
        seen.add(cik)
        name=cik+"-"+digest+".json"
        if ref["path"]!=name:raise ValueError("invalid file path")
        p=root/name
        if p.is_symlink() or p.stat().st_size>8_000_000:raise ValueError("file bound")
        raw=p.read_bytes()
        if sha(raw)!=digest:raise ValueError("file checksum")
        d=json.loads(raw)
        if set(d)!={"schemaVersion","issuerCIK","source","archive","records","notice"} or d["schemaVersion"]!=1 or d["issuerCIK"]!=cik or d["source"]!=SOURCE or d["archive"]!=meta:raise ValueError("evidence envelope")
        rows=d["records"]
        if not isinstance(rows,list) or type(ref["records"]) is not int or len(rows)!=ref["records"]:raise ValueError("row count")
        keys=set()
        for r in rows:
            allowed={"accession","table","sourceRowKey","form","filingDate","transactionDate","code","direction","amendment","filingUrl"}
            if r["table"]=="NONDERIV_TRANS":allowed|={"securityTitle","reportedShares","reportedPricePerShare"}
            elif r["table"]!="DERIV_TRANS":raise ValueError("table")
            if set(r)!=allowed:raise ValueError("unexpected evidence fields")
            key=(r["accession"],r["table"],r["sourceRowKey"])
            if key in keys:raise ValueError("duplicate evidence")
            keys.add(key)
        count+=len(rows);nonempty+=bool(rows)
        objects.append((f"sec-insider/v1/issuers/{cik}/{digest}.json",raw))
    if (index["issuers"],index["issuersWithRecords"],index["records"])!=(len(seen),nonempty,count) or count==0:raise ValueError("manifest coverage")
    receipt=encode({"schemaVersion":1,"sourceArchive":meta,"manifestSha256":sha(manifest),"issuers":len(seen),"records":count,"objects":[{"key":k,"sha256":sha(b),"bytes":len(b)} for k,b in objects],"publicPublication":False,"status":"readback_verified"})
    return objects,(f"sec-insider/v1/receipts/{sha(receipt)}.json",receipt),count

def put_verified(client,key,raw):
    status=immutable_put(client,raw,key,{"dataset":"sec-insider","publicpublication":"false"},"application/json")
    stream=client.get_object(Bucket=BUCKET,Key=key)["Body"]
    try:actual=stream.read(len(raw)+1)
    finally:stream.close()
    if len(actual)!=len(raw) or sha(actual)!=sha(raw):raise ValueError("R2 readback mismatch")
    return status

def archive(client,root):
    objects,receipt,count=prepare(root)
    states=[put_verified(client,k,b) for k,b in objects]
    put_verified(client,*receipt)
    return {"dataset":"sec-insider","issuers":len(objects),"records":count,"created":states.count("created"),"alreadyPresent":states.count("already_present"),"receiptKey":receipt[0],"readbackVerified":True,"publicPublication":False}

def main():
    account=configuration(os.environ,smoke_only=True)
    import boto3
    from botocore.config import Config
    client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",
        aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
    print("SEC_INSIDER_R2_VERIFIED "+json.dumps(archive(client,ROOT/"validation-artifacts/sec-insider"),sort_keys=True))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("SEC_INSIDER_R2_FAILED "+type(exc).__name__)
        raise SystemExit(1) from None
