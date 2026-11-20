"""Compact reusable index plus opt-in immutable storage of reviewed official data.

Latest published JSON remains the source of truth. Git retains revisions.
Never archive exchange quotes, news, registry personal data, tokens or
restricted preview results. R2 is a separate, private, explicitly enabled sink.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
FILES=(
 "data/free-research.json","data/open-data.json","data/economic-feeds.json",
 "data/entsoe-open.json","data/shipping-open.json","data/shipping-ports.json",
 "data/shipping-connectivity.json","data/instrument-directory.json",
 "data/research-coverage.json","data/history-coverage.json",
 "data/issuer-identities.json","data/fundamentals.json","data/freight-routes.json",
 "data/licensed-price-coverage.json","data/source-health.json","data/news-quality.json",
 "data/global-indices-v1.json","data/global-index-tpex.json","data/global-index-formosa.json",
 "data/esma-equity-history/index.json",
)
# Exact reviewed public statistical datasets only. No catch-all 'open' policy.
APPROVED={
 "eurostat-production":("eurostat","ec.europa.eu","Eurostat reuse policy"),
 "ssb-production":("ssb","data.ssb.no","CC BY 4.0"),
 "sodir-fields":("sodir","factmaps.sodir.no","NLOD 2.0"),
 "sodir-owner-history":("sodir","factmaps.sodir.no","NLOD 2.0"),
 "finland-production":("statfin","pxdata.stat.fi","CC BY 4.0"),
 "denmark-production":("dst","api.statbank.dk","CC BY 4.0"),
 "usgs-mineral-statistics":("usgs","www.sciencebase.gov","USGS public domain / CC0"),
 "norges-bank-policy":("norges_bank","data.norges-bank.no","NLOD 2.0"),
}
def stamp():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(root,path):
    p=root/path
    if p.stat().st_size>32_000_000:raise ValueError("file_limit")
    raw=p.read_bytes();d=json.loads(raw)
    if not isinstance(d,dict):raise ValueError("invalid_dataset")
    return raw,d
def txt(x):return x if isinstance(x,str) else None
def rows(x):
    for k in ("records","history","points","observations"):
        if isinstance(x.get(k),list):return x[k]
    return None
def count(x):
    r=rows(x)
    return len(r) if r is not None else None
def summarize(x,path,outer):
    key=x.get("id") or x.get("key")
    if not isinstance(key,str) or not key:return None
    status=x.get("status")
    if not isinstance(status,str):
        providers=outer.get("sources")
        provider=x.get("provider")
        if isinstance(providers,dict) and isinstance(providers.get(provider),dict):
            status=providers[provider].get("status")
        elif isinstance(outer.get("source"),dict):
            status=outer["source"].get("status")
    return {"id":key,"label":txt(x.get("title") or x.get("label")) or key,
      "path":path,"provider":txt(x.get("provider")),"unit":txt(x.get("unit")),
      "frequency":txt(x.get("frequency")),"records":count(x),
      "status":txt(status) or "not_reported",
      "period":txt(x.get("period") or x.get("endUtc")),
      "retrievedAt":txt(x.get("retrievedAt") or x.get("observedAt")),
      "license":txt(x.get("license") or outer.get("license")),
      "dimensions":[txt(v.get("id")) for v in x.get("dimensions",[]) if isinstance(v,dict) and isinstance(v.get("id"),str)]}
def index(root=ROOT):
    files=[];datasets=[]
    for path in FILES:
        try:raw,d=read(root,path)
        except (OSError,ValueError,TypeError):
            files.append({"path":path,"status":"unavailable"});continue
        units=d.get("datasets") if path=="data/free-research.json" else d.get("series")
        entries=[]
        if isinstance(units,list):
            for x in units:
                if isinstance(x,dict):
                    item=summarize(x,path,d)
                    if item:entries.append(item)
        if path in ("data/global-indices-v1.json","data/global-index-tpex.json","data/global-index-formosa.json"):
            item=summarize({**d,"label":d.get("name"),"unit":"index points","frequency":"daily","period":d.get("latest",{}).get("date"),"retrievedAt":d.get("lastSuccessAt")},path,d)
            if item:entries.append(item)
        datasets.extend(entries)
        r=rows(d)
        # Series counts and observation counts are distinct; no overall
        # total that would double-count overlapping sources or revisions.
        n=sum(x["records"] for x in entries if x["records"] is not None) if entries else len(r) if r is not None else None
        files.append({"path":path,"status":"indexed","bytes":len(raw),"sha256":sha(raw),
          "gitBlobSha":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),
          "generated":txt(d.get("generated")),"seriesOrDatasets":len(entries),"recordCount":n})
    out={"schemaVersion":1,"generated":stamp(),"files":files,"datasets":datasets,
      "history":{"method":"Git revision history of each published file; content hashes verify integrity. Private R2 archive is separately enabled and must be validated.","repository":"https://github.com/LordOfTheIdiot5/stockwatch"},
      "relatedCatalogs":[{"id":"energy-nordl","url":"https://energy.nordl.dev/data/commercial-catalog-v1.json","status":"external_catalog_link","note":"External source; availability and rights not inferred."}],
      "notice":"Counts are source-level records, not unique economic observations, issuers or authorized quote coverage. No credentials or restricted records included."}
    dest=root/"data/research-index.json";tmp=dest.with_suffix(".tmp");tmp.write_bytes(canonical(out)+b"\n");tmp.replace(dest)
    print("RESEARCH_INDEX "+json.dumps({"files":len(files),"datasets":len(datasets),"bytes":dest.stat().st_size}))
    return out
def eligible(dataset):
    if not isinstance(dataset,dict):return False
    policy=APPROVED.get(dataset.get("id"))
    if not policy:return False
    provider,host,license_prefix=policy
    u=urlsplit(str(dataset.get("sourceUrl","")))
    return (dataset.get("provider")==provider and dataset.get("status")=="ok"
        and u.scheme=="https" and u.hostname==host and not u.username and not u.password
        and isinstance(dataset.get("license"),str) and dataset["license"].startswith(license_prefix)
        and isinstance(dataset.get("records"),list) and bool(dataset["records"])
        and isinstance(dataset.get("retrievedAt"),str))
def archive_objects(dataset):
    if not eligible(dataset):raise ValueError("dataset_not_approved")
    # Preserve the complete dataset including sourceUpdated, field units,
    # observations, attributes and original licensing. Only collection
    # telemetry changes are held separately in a receipt.
    payload={k:v for k,v in dataset.items() if k not in ("retrievedAt","checkedAt","status","errorType","httpStatus")}
    raw=canonical(payload)
    if len(raw)>12_000_000:raise ValueError("archive_size_limit")
    digest=sha(raw);ident=dataset["id"]
    key=f"official-open/v1/{ident}/objects/{digest}.json.gz"
    compressed=gzip.compress(raw,mtime=0)
    receipt={"schemaVersion":1,"datasetId":ident,"retrievedAt":dataset["retrievedAt"],"sourceUrl":dataset["sourceUrl"],"license":dataset["license"],"objectKey":key,"uncompressedSha256":digest,"compressedSha256":sha(compressed),"records":len(dataset["records"])}
    rec=canonical(receipt)
    return key,compressed,f"official-open/v1/{ident}/receipts/{sha(rec)}.json",rec
def archive(root=ROOT,client=None,env=None):
    env=os.environ if env is None else env
    if env.get("STOCKWATCH_OPEN_DATA_ARCHIVE_ENABLED")!="true":raise PermissionError("open_archive_not_enabled")
    from private_r2_archive import configuration,immutable_put
    account=configuration(env,smoke_only=True)
    if client is None:
        import boto3
        from botocore.config import Config
        client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",
            aws_access_key_id=env["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=env["STOCKWATCH_R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":2,"mode":"standard"}))
    _,d=read(root,"data/free-research.json")
    out=[]
    for x in d.get("datasets",[]):
        if not eligible(x):continue
        key,body,rkey,receipt=archive_objects(x)
        result=immutable_put(client,body,key,{"provider":x["provider"],"dataset":x["id"]},"application/gzip")
        immutable_put(client,receipt,rkey,{"dataset":x["id"]},"application/json")
        out.append({"id":x["id"],"status":result,"compressedBytes":len(body)})
    print("OFFICIAL_R2_ARCHIVE "+json.dumps(out))
    if not out:raise ValueError("no_approved_datasets")
    return out
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--archive",action="store_true");args=a.parse_args()
    if args.archive:archive()
    else:index()
