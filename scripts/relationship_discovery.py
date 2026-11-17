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
KINDS={"supplies","supply_contract","service_contract","equity_investment","financing","debt_repayment","arrangement"}
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
        if a is not None and (type(a.get("value")) is not int or a["value"]<=0 or not re.fullmatch(r"[A-Z]{3}",a["currency"]) or a["comparison"] not in {"exact_reported","greater_than","approximate","up_to"} or not a.get("basis")):
            raise ValueError("Invalid amount")
        ids.add(e["id"])
    return entities

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
        key=hashlib.sha256((s["url"]+"|"+mode+"|"+"|".join(matched)+"|"+str(ticker)).encode()).hexdigest()
        row={"id":key,"newsId":s["id"],"entityIds":matched,"issuerTicker":ticker,"candidateType":mode,"published":s["published"],"sourceUrl":s["url"],"status":"review_required","relationshipVerified":False,"amount":None}
        if key not in candidates or row["newsId"]<candidates[key]["newsId"]:candidates[key]=row
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
    candidates=discover(graph,items)
    out={"schemaVersion":1,"generated":datetime.now(timezone.utc).isoformat(),"newsRecordsScanned":len(items),"notice":"Metadata-only leads, not evidence-backed relationships. Source review required; no headlines or article text copied.","candidates":candidates}
    p=root/OUT;tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8");tmp.replace(p)
    print(json.dumps({"newsRecordsScanned":len(items),"verifiedSeedRelationships":len(graph["relationships"]),"reviewCandidates":len(candidates)}))
    return out

if __name__=="__main__":run()
