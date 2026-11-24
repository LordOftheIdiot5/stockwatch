"""Discover relationship review leads from existing archived news metadata.

Never converts a headline, company co-mention or event keyword into a fact.
No external downloads, no new full-text collection, no inferred currency or value.
"""
from __future__ import annotations
import hashlib,json,re,unicodedata
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
REL=Path("data/company-relationships.json")
OUT=Path("data/relationship-review.json")
KINDS={"supplies","supply_contract","service_contract","equity_investment","financing","debt_repayment","arrangement","acquisition","partnership","asset_transfer"}
EVENT_WORDS=re.compile(r"\b(contract|order|supply|supplier|partner(?:ship)?|financ(?:ing|es)|loan|invest(?:s|ed|ment)?|acqui(?:res|sition)|customer|deal|agreement|leverandør|kontrakt|avtale)\b",re.I)
def textnorm(s):
    return unicodedata.normalize("NFKC",str(s or "")).casefold()

def safe_url(s):
    try:
        p=urlsplit(s)
        return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password
    except (TypeError,ValueError):return False

def day(s):
    try:return date.fromisoformat(s).isoformat()==s
    except (ValueError,TypeError):return False

def validate(graph):
    if graph.get("schemaVersion")!=1 or not day(graph.get("compiledOn")):raise ValueError("Invalid graph")
    entities={}
    for e in graph["entities"]:
        if not re.fullmatch(r"[a-z0-9-]+",e["id"]) or e["id"] in entities or not e["name"] or not e["aliases"]:
            raise ValueError("Invalid entity")
        entities[e["id"]]=e
    ids=set()
    for e in graph["relationships"]:
        if e["id"] in ids or e["from"]==e["to"] or e["from"] not in entities or e["to"] not in entities or e["type"] not in KINDS:
            raise ValueError("Invalid relationship")
        if e["evidenceStatus"]!="issuer_disclosed" or e.get("actualCashFlow") is not False or not safe_url(e["sourceUrl"]) or not e["sourceLocator"]:
            raise ValueError("Unreviewed relationship")
        if not all(day(e.get(k)) for k in ("disclosedOn","reviewedOn")) or not e["disclosedOn"]<=e["reviewedOn"]<=graph["compiledOn"]:
            raise ValueError("Invalid evidence chronology")
        if e.get("eventOn") and (not day(e["eventOn"]) or e["eventOn"]>e["disclosedOn"]):raise ValueError("Invalid event date")
        a=e["amount"]
        if a is not None and (type(a.get("value")) is not int or a["value"]<=0 or not re.fullmatch(r"[A-Z]{3}",a["currency"]) or a["comparison"] not in {"exact_reported","greater_than","approximate","up_to","range"} or not a.get("basis")):
            raise ValueError("Invalid amount")
        if a is not None and a["comparison"]=="range" and (type(a.get("upperValue")) is not int or a["upperValue"]<=a["value"]):raise ValueError("Invalid contract range")
        ids.add(e["id"])
    return entities

def lead_key(url,ticker):
    # Stable across alias additions, classifier changes and candidate promotion.
    return hashlib.sha256(json.dumps([url,ticker],separators=(",",":")).encode()).hexdigest()

def merge_review(previous,current,graph,now):
    """Reconcile metadata across refreshes; preserve previously discovered leads."""
    stored={}
    known=set(validate(graph))
    for rows,is_new in ((previous,False),(current,True)):
        for row in rows:
            if not isinstance(row,dict) or not safe_url(row.get("sourceUrl")) or not isinstance(row.get("newsId"),str):continue
            ticker=row.get("issuerTicker")
            if ticker is not None and not isinstance(ticker,str):continue
            key=lead_key(row["sourceUrl"],ticker)
            old=stored.get(key)
            ids=sorted(set([row["newsId"]]+[x for x in row.get("newsIds",[]) if isinstance(x,str)]+(old["newsIds"] if old else [])))
            aliases=sorted(set(x for x in row.get("entityIds",[])+(old["entityIds"] if old else []) if x in known))
            first=old["firstSeenAt"] if old else row.get("firstSeenAt")
            item={"id":key,"newsId":ids[0],"newsIds":ids,"entityIds":aliases,"issuerTicker":ticker,
                  "candidateType":row.get("candidateType","headline_event"),"published":min(row["published"],old["published"]) if old else row["published"],
                  "sourceUrl":row["sourceUrl"],"status":"review_required","relationshipVerified":False,"amount":None,
                  "firstSeenAt":first or now,"lastSeenAt":now if is_new else row.get("lastSeenAt") or now,
                  "currentlyDetected":is_new}
            stored[key]=item
    reviewed={}
    for e in graph["relationships"]:
        if e.get("discoveryNewsId"):reviewed.setdefault(e["discoveryNewsId"],set()).add(e["id"])
    for row in stored.values():
        linked=set().union(*(reviewed.get(n,set()) for n in row["newsIds"]))
        if linked:
            row["status"]="related_evidence_recorded"
            row["relatedRelationshipIds"]=sorted(linked)
    return sorted(stored.values(),key=lambda r:(r["published"],r["id"]))

def discover(graph,items):
    entities=validate(graph)
    aliases={}
    for e in entities.values():
        for a in e["aliases"]:
            key=textnorm(a)
            aliases.setdefault(key,set()).add(e["id"])
    patterns=[(re.compile(r"(?<!\w)"+re.escape(a)+r"(?!\w)"),next(iter(ids))) for a,ids in aliases.items() if len(a)>=4 and len(ids)==1]
    candidates={}
    for s in items:
        if not isinstance(s,dict) or s.get("duplicateOf") or not safe_url(s.get("url")) or not s.get("id") or not isinstance(s.get("published"),str):
            continue
        try:
            stamp=datetime.fromisoformat(s["published"].replace("Z","+00:00"))
            if stamp.tzinfo is None:continue
        except ValueError:continue
        h=textnorm(s.get("english") or s.get("headline"))
        if not EVENT_WORDS.search(h):continue
        matched=sorted({eid for p,eid in patterns if p.search(h)})
        # Also queue issuer-linked event disclosures for counterparty discovery.
        # An unknown counterparty is not silently added to the graph.
        official=s.get("type")=="disclosure" and s.get("match")=="issuer_code" and s.get("relevance")=="strong" and isinstance(s.get("ticker"),str) and bool(s["ticker"])
        associated=s.get("match")=="name_mentioned" and s.get("relevance") in ("strong","mentioned") and isinstance(s.get("ticker"),str) and bool(s["ticker"])
        if len(matched)<2 and not official and not associated:continue
        mode="co_mention" if len(matched)>=2 else "issuer_event" if official else "headline_event"
        ticker=s["ticker"] if official or associated else None
        key=lead_key(s["url"],ticker)
        row={"id":key,"newsId":s["id"],"entityIds":matched,"issuerTicker":ticker,"candidateType":mode,"published":s["published"],"sourceUrl":s["url"],"status":"review_required","relationshipVerified":False,"amount":None}
        prior=candidates.get(key)
        if prior:
            row["entityIds"]=sorted(set(prior["entityIds"]+row["entityIds"]))
            row["newsIds"]=sorted(set(prior["newsIds"]+[row["newsId"]]))
            if prior["published"]<row["published"]:row["published"]=prior["published"]
            row["newsId"]=row["newsIds"][0]
        else:row["newsIds"]=[row["newsId"]]
        candidates[key]=row
    return sorted(candidates.values(),key=lambda x:(x["published"],x["id"]))

def archived_items(root):
    # Month partitions are the existing archive of record. Fall back to the
    # rolling news archive only when the partition index does not exist.
    index=root/"data/news-store/index.json"
    if not index.exists():
        d=json.loads((root/"data/news-archive.json").read_text(encoding="utf8"))
        yield from d.get("items",[])
        return
    d=json.loads(index.read_text(encoding="utf8"))
    for row in d.get("months",[]):
        month=row["month"]
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",month):raise ValueError("Invalid month")
        p=root/"data/news-store"/(month+".json")
        z=json.loads(p.read_text(encoding="utf8"))
        yield from z.get("items",[])

def run(root=ROOT):
    graph=json.loads((root/REL).read_text(encoding="utf8"))
    items=list(archived_items(root))
    now=datetime.now(timezone.utc).isoformat()
    p=root/OUT
    previous=json.loads(p.read_text(encoding="utf8")) if p.exists() else {}
    # Legacy rows had no observation timestamps; use the previous file's
    # generation time as the earliest locally documented discovery.
    old=[{**r,"firstSeenAt":r.get("firstSeenAt") or previous.get("generated"),"lastSeenAt":r.get("lastSeenAt") or previous.get("generated")} for r in previous.get("candidates",[])]
    candidates=merge_review(old,discover(graph,items),graph,now)
    out={"schemaVersion":1,"generated":now,"newsRecordsScanned":len(items),"notice":"Metadata-only leads, not evidence-backed relationships. Source review required; no headlines or article text copied.","candidates":candidates,
         "relatedEvidenceLeadCount":sum(r["status"]=="related_evidence_recorded" for r in candidates),
         "currentlyDetectedCount":sum(r["currentlyDetected"] for r in candidates)}
    p=root/OUT;tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8");tmp.replace(p)
    print(json.dumps({"newsRecordsScanned":len(items),"verifiedSeedRelationships":len(graph["relationships"]),"reviewCandidates":len(candidates)}))
    return out

if __name__=="__main__":run()
