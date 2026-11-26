"""N41 private-company news: reuse existing open-web metadata provider.

Separate research identities from traded securities; no automatic IPO
promotion, quote inputs, article bodies, alerts or new licensed feeds.
"""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError
from news_quality import has_phrase, norm, topic

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/unlisted-news-reviewed-n41.json"
OUTPUT = ROOT / "data/unlisted-news-latest-n41.json"
LIMIT = 15
DAYS = 30


def candidate(company, raw, now):
    title = raw.get("title")
    url = raw.get("url")
    publisher = raw.get("publisher")
    if not all(isinstance(x, str) and x.strip() for x in (title, url, publisher)):
        return None
    if raw.get("junk") or len(title)>500 or len(url)>4096 or len(publisher)>150:
        return None
    if not any(has_phrase(title, alias) for alias in company["aliases"]):
        return None
    try:
        u = urlsplit(url)
        if (u.scheme != "https" or u.netloc != "news.google.com"
                or not u.path.startswith("/rss/articles/")):
            return None
        date = parsedate_to_datetime(raw.get("published", ""))
        if date.tzinfo is None:
            return None
        date = date.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None
    if date > now or date < now-timedelta(days=DAYS):
        return None
    return {"id": "web-"+hashlib.sha256((company["id"]+"\n"+url).encode()).hexdigest(),
            "company": company["id"], "date": date.isoformat(), "category": topic(title),
            "title": title, "url": url, "publisher": publisher,
            "tier": "named reference", "dateType": "reported publication time"}


def collect(registry, prior, fetch, now):
    items, status = [], {}
    unavailable = None
    for company in registry["companies"]:
        ident = company["id"]
        old = [x for x in prior.get("items",[]) if x.get("company")==ident
               and x.get("tier")=="named reference"]
        rows = []
        error = None
        try:
            if unavailable is not None:
                raise HTTPError("", unavailable, "provider unavailable", {}, None)
            raw = fetch(company["aliases"][0], count=LIMIT, locale="en")
            rows = [x for item in raw[:LIMIT] if (x:=candidate(company,item,now))]
            state = "named_references_observed" if rows else "no_usable_results_or_unconfirmed"
        except HTTPError as exc:
            state = "provider_http_error" if unavailable is None else "provider_skipped_after_error"
            error = exc.code
            if exc.code in (429, 503):
                unavailable = exc.code
        except Exception:
            state = "unconfirmed"
        seen = set()
        for item in sorted(rows+old,key=lambda x:x["date"],reverse=True):
            try:
                stamp=datetime.fromisoformat(item["date"])
                if stamp.tzinfo is None or not now-timedelta(days=DAYS)<=stamp<=now:
                    continue
                key=norm(item["title"])
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(item)
                if len(seen)>=LIMIT:
                    break
            except (KeyError, ValueError, TypeError):
                continue
        status[ident]={"status":state,"freshNamedReferences":len(rows),
                       "retainedReferences":len(seen)}
        if error is not None:
            status[ident]["httpStatus"] = error
    return {"schema":1,"attemptedAt":now.isoformat(),"items":items,"coverage":status,
            "notice":"Open-web headline references only; no verified issuer event, IPO or trading status inferred."}


def main():
    import sources
    registry=json.loads(SEED.read_text(encoding="utf-8"))
    previous=json.loads(OUTPUT.read_text(encoding="utf-8"))
    doc=collect(registry,previous,lambda *a,**k: sources.news(*a,**k,strict=True),datetime.now(timezone.utc))
    temp=OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp.replace(OUTPUT)
    print(json.dumps({"attemptedAt":doc["attemptedAt"],"coverage":doc["coverage"],"count":len(doc["items"])}))


if __name__=="__main__":
    main()
