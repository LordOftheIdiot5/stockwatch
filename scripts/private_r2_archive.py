"""Private R2 archive for reviewed Euronext internal retention only.

No public bucket, URL, download route, CI artifact or dataset publication.
Content-addressed immutable objects retain changed reports without overwrites.
Collection timestamp is not the trading session date.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from datetime import datetime,timezone
from pathlib import Path
import delayed_exchange as ex

BUCKET="stockwatch-private-market-history"
WINDOWS=("CURRENT_TRADING_DAY","PREVIOUS_TRADING_DAY")
def configuration(env, *, smoke_only=False):
    if not smoke_only and env.get("STOCKWATCH_R2_RETENTION_APPROVED")!="true":
        raise ValueError("Internal retention and private storage must be reviewed before activation")
    account=env.get("STOCKWATCH_R2_ACCOUNT_ID","")
    if not re.fullmatch(r"[a-fA-F0-9]{32}",account):raise ValueError("Invalid R2 account ID")
    if env.get("STOCKWATCH_R2_BUCKET")!=BUCKET:raise ValueError("Dedicated private bucket required")
    if not env.get("STOCKWATCH_R2_ACCESS_KEY_ID") or not env.get("STOCKWATCH_R2_SECRET_ACCESS_KEY"):
        raise ValueError("Missing scoped R2 credentials")
    return account
def immutable_put(client,body,key,metadata,content_type):
    digest=hashlib.sha256(body).hexdigest()
    meta={**metadata,"sha256":digest}
    try:
        client.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType=content_type,
            Metadata=meta,IfNoneMatch="*")
        result="created"
    except Exception as exc:
        response=getattr(exc,"response",{})
        if response.get("ResponseMetadata",{}).get("HTTPStatusCode")!=412:raise
        prior=client.head_object(Bucket=BUCKET,Key=key)
        if prior.get("Metadata",{}).get("sha256")!=digest or prior.get("ContentLength")!=len(body):
            raise ValueError("Existing content-addressed object failed integrity check") from None
        result="already_present"
    return result
def archive(client,market,window,fetch=ex.downloaded,now=None):
    if window not in WINDOWS:raise ValueError("Ordinary daily report windows only")
    raw=fetch(ex.eur_url(market,window))
    ex.csv_schema(raw)
    stamp=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    digest=hashlib.sha256(raw).hexdigest()
    key=f"euronext/{market}/objects/{digest}.zip"
    action=immutable_put(client,raw,key,{"provider":"euronext","market":market},"application/zip")
    # Every retrieval gets a separate, private provenance record. The raw ZIP
    # is deduplicated across dates and overlapping current/previous downloads.
    receipt={"schemaVersion":1,"provider":"Euronext","market":market,"window":window,
        "retrievedAt":stamp,"sourceUrl":ex.eur_url(market,window),"objectKey":key,
        "sha256":digest,"schemaValidated":True,"officialClose":False,
        "publicPublicationAllowed":False}
    payload=json.dumps(receipt,sort_keys=True,separators=(",",":")).encode()
    receipt_key=f"euronext/{market}/receipts/{stamp[:10]}/{hashlib.sha256(payload).hexdigest()}.json"
    immutable_put(client,payload,receipt_key,{"provider":"euronext","market":market},"application/json")
    return action
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",choices=ex.MARKETS,default="OSL")
    p.add_argument("--smoke-test",action="store_true",help="Write synthetic marker only, no exchange download")
    a=p.parse_args()
    try:
        account=configuration(os.environ, smoke_only=a.smoke_test)
        import boto3
        from botocore.config import Config
        client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=120,
                          retries={"max_attempts":3,"mode":"standard"}))
        if a.smoke_test:
            marker=b"Stockwatch synthetic private storage test v1"
            immutable_put(client,marker,"system/smoke-v1.txt",{"type":"synthetic"},"text/plain")
            print("Private R2 smoke test passed; no market data retrieved.")
            return 0
        for window in WINDOWS:
            result=archive(client,a.market,window)
            print(json.dumps({"market":a.market,"window":window,"storageStatus":result,"publicPublication":False}))
        return 0
    except Exception as exc:
        # Do not log credentials, presigned URLs, archive payloads or vendor responses.
        print(json.dumps({"status":"failed","errorType":type(exc).__name__,"publicPublication":False}))
        return 1
if __name__=="__main__":sys.exit(main())
