"""Import only the reviewed company photograph catalog; no arbitrary search/scraping.

Retains source credits and produces optimized local WebP copies. CC BY-SA
copies remain under their original share-alike license. Run with Pillow.
"""
from __future__ import annotations
import argparse, hashlib, io, json, re, urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
CATALOG=Path("data/company-image-catalog.json")
MAX_INPUT=12*1024*1024
MAX_OUTPUT=250*1024
HOSTS={"thumb.wikimedia.org","upload.wikimedia.org"}
LICENSES={
    "CC BY 2.0":"https://creativecommons.org/licenses/by/2.0/",
    "CC BY 4.0":"https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0":"https://creativecommons.org/licenses/by-sa/4.0/",
    "CC0 1.0":"https://creativecommons.org/publicdomain/zero/1.0/",
}

def validate(a):
    if not re.fullmatch(r"[a-z0-9-]+",a["id"]) or a["localAsset"]!="assets/company/"+a["id"]+".webp":
        raise ValueError("Unexpected asset path")
    if a["license"] not in LICENSES or a["licenseUrl"]!=LICENSES[a["license"]]:
        raise ValueError("Unsupported photo license")
    if not re.fullmatch(r"commons_file_license_reviewed_\d{4}-\d{2}-\d{2}",a["rightsReview"]):
        raise ValueError("Photo must be reviewed")
    if not all(isinstance(a.get(k),str) and a[k].strip() for k in ("listing","author","caption","alt","capturedOn")):
        raise ValueError("Missing photo attribution")
    p=urlparse(a["sourcePage"]);q=urlparse(a["downloadUrl"])
    if p.scheme!="https" or p.netloc!="commons.wikimedia.org" or not p.path.startswith("/wiki/File:"):
        raise ValueError("Invalid source page")
    if q.scheme!="https" or q.netloc not in HOSTS or not q.path.startswith("/wikipedia/commons/"):
        raise ValueError("Invalid download host")
    return a

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"NordlStockwatchPhotoImport/1.0 (+https://stocks.nordl.dev/)","Accept":"image/jpeg,image/png,image/webp"})
    with urllib.request.urlopen(req,timeout=45) as response:
        dest=urlparse(response.geturl())
        if dest.scheme!="https" or dest.netloc not in HOSTS:
            raise ValueError("Unexpected image redirect")
        if response.headers.get_content_type() not in {"image/jpeg","image/png","image/webp"}:
            raise ValueError("Not a supported image response")
        raw=response.read(MAX_INPUT+1)
    if len(raw)>MAX_INPUT:raise ValueError("Photo exceeds input budget")
    return raw

def optimize(raw):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS=30_000_000
    with Image.open(io.BytesIO(raw)) as im:
        im.verify()
    with Image.open(io.BytesIO(raw)) as im:
        if im.format not in {"JPEG","PNG","WEBP"} or getattr(im,"is_animated",False):
            raise ValueError("Unsupported image")
        im=ImageOps.exif_transpose(im).convert("RGB")
        if im.width<800 or im.height<400:raise ValueError("Photo resolution too small")
        im.thumbnail((1280,960),Image.Resampling.LANCZOS)
        for q in (84,78,72,65,58):
            buf=io.BytesIO();im.save(buf,format="WEBP",quality=q,method=6)
            if len(buf.getvalue())<=MAX_OUTPUT:return buf.getvalue(),im.size
    raise ValueError("Unable to meet image budget")

def run(root=ROOT,fetcher=fetch,check_only=False):
    p=root/CATALOG;doc=json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schemaVersion")!=1 or not doc.get("assets"):raise ValueError("Invalid photo catalog")
    seen=set();staged=[]
    for a in doc["assets"]:
        validate(a)
        if a["id"] in seen:raise ValueError("Duplicate photo ID")
        seen.add(a["id"])
        raw=fetcher(a["downloadUrl"])
        content,size=optimize(raw)
        staged.append((a,content,size,hashlib.sha256(raw).hexdigest()))
    if not check_only:
        # Complete the downloads and validation before publishing any files.
        for a,content,size,original_hash in staged:
            out=root/a["localAsset"];out.parent.mkdir(parents=True,exist_ok=True)
            tmp=out.with_suffix(".tmp");tmp.write_bytes(content);tmp.replace(out)
            a.update(status="imported",sha256=hashlib.sha256(content).hexdigest(),sourceSHA256=original_hash,
                     bytes=len(content),width=size[0],height=size[1],
                     transformations="Resized, converted to WebP; original license retained; no endorsement.")
        tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(p)
    for a,content,size,_ in staged:
        print(json.dumps({"asset":a["id"],"bytes":len(content),"width":size[0],"height":size[1],"checkOnly":check_only}))
    return len(staged)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args();run(check_only=args.check_only)
