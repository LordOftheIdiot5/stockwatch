"""In-memory, reference-only Cboe instrument overlap audit and direct-feed discovery.

No raw trade downloads, price fields, RICs or identifiers logged or retained.
No agreement is accepted; Xetra terms gate is not bypassed.
"""
from __future__ import annotations
import csv,io,json,re,unicodedata,os
from collections import Counter,defaultdict
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
HOST="accounteu.cboe.com"
BOOKS=("dxe","cxe","bxe")
MIC={"OL":"XOSL","ST":"XSTO","CO":"XCSE","HE":"XHEL","DE":"XETR","PA":"XPAR","MI":"XMIL","BR":"XBRU","AS":"XAMS","IR":"XDUB","VI":"XWBO","MC":"XMAD","HK":"XHKG"}
CCY={"OL":"NOK","ST":"SEK","CO":"DKK","HE":"EUR","DE":"EUR","PA":"EUR","MI":"EUR","BR":"EUR","AS":"EUR","IR":"EUR","VI":"EUR","MC":"EUR","HK":"HKD"}
SOURCES={"cboe_transparency":"https://www.cboe.com/markets/eu/equities/transparency-data/",
         "xetra_posttrade":"https://mfs.deutsche-boerse.com/DETR-posttrade"}
MAX=12*1024*1024
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def fetch(url):
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname not in {HOST,"www.cboe.com","mfs.deutsche-boerse.com","registers.esma.europa.eu"} or p.username or p.password:raise ValueError("unapproved_url")
    req=Request(url,headers={"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev/)"})
    with build_opener(NoRedirect()).open(req,timeout=45) as response:
        data=response.read(MAX+1)
    if len(data)>MAX:raise ValueError("download_limit")
    return data
def isin_ok(s):
    if not isinstance(s,str) or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]",s):return False
    digits="".join(str(ord(c)-55) if c.isalpha() else c for c in s)
    return sum(sum(map(int,str(int(c)*(2 if i%2 else 1)))) for i,c in enumerate(reversed(digits)))%10==0
def normalized(s):
    # No deletion of company suffixes or share-class markers. Exact normalized
    # legal names only suggest a review candidate, never a verified identity.
    return " ".join(re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()).split())
def reference(raw,now):
    lines=io.StringIO(raw.decode("utf-8-sig"),newline="")
    descriptor=dict(x.split("=",1) for x in next(csv.reader([lines.readline()])) if "=" in x)
    if descriptor.get("environment")!="PROD":raise ValueError("nonproduction_reference")
    created=date.fromisoformat(descriptor["created"])
    if created>now.date() or (now.date()-created).days>4:raise ValueError("outside_reference_window")
    reader=csv.DictReader(lines)
    required={"isin","mic","currency","company_name","live","asset_class","bats_name"}
    if not required.issubset(reader.fieldnames or []):raise ValueError("unknown_reference_schema")
    items=set();total=0
    for row in reader:
        total+=1
        if total>100000:raise ValueError("row_limit")
        if row["live"]!="t" or row["asset_class"]!="EQTY" or not isin_ok(row["isin"]):continue
        if not re.fullmatch(r"[A-Z0-9]{4}",row["mic"]) or not re.fullmatch(r"[A-Z]{3}",row["currency"]):continue
        items.add((row["isin"],row["mic"],row["currency"],normalized(row["company_name"]),row["bats_name"]))
    if not items:raise ValueError("empty_equity_reference")
    return items,{"referenceDate":str(created),"rows":total,"activeEquityIdentities":len({x[:3] for x in items}),"warningPresent":bool(descriptor.get("warning"))}
# Candidate-only UMTF matching: exact symbol stem after removing the
# share-class separator, plus primary MIC/currency, then independent FIGI.
UMTF={"OL":"o","ST":"s","CO":"c","HE":"h","DE":"d","PA":"p","MI":"m","BR":"b","AS":"a","MC":"e"}
def candidate_keys(watch,figis,items):
    existing={x["ticker"]:x for x in figis if x.get("match")=="single_instrument_same_mic_candidate" and x.get("figi")}
    by_name=defaultdict(set);by_symbol=defaultdict(set)
    for isin,mic,ccy,name,symbol in items:
        by_name[mic,ccy,name].add((isin,mic))
        by_symbol[mic,ccy,symbol].add((isin,mic))
    selected=set();counts=Counter();rows=[]
    for row in watch:
        ticker=row["ticker"];stem,suffix=ticker.rsplit(".",1);mic=MIC.get(suffix);ccy=CCY.get(suffix)
        prev=existing.get(ticker)
        if not prev:counts["no_prior_figi"]+=1;continue
        rows.append({"id":ticker,"mic":mic,"figi":prev["figi"],"isin":None})
        names=by_name[mic,ccy,normalized(prev.get("name",""))]|by_name[mic,ccy,normalized(row["name"])]
        # Keep class A/B letters. Unknown suffixes are not guessed.
        sym=stem.replace("-","")+UMTF.get(suffix,"") if suffix in UMTF else ""
        keys=names|by_symbol[mic,ccy,sym]
        if len(keys)>8:counts["too_many_candidates"]+=1;continue
        if keys:counts["candidate_found"]+=1;selected.update(keys)
        else:counts["no_reference_candidate"]+=1
    if len(selected)>500:raise ValueError("mapping_budget")
    return sorted(selected),rows,dict(counts)
FIRDS="https://registers.esma.europa.eu/solr/esma_registers_firds/select"
def firds_check(matches,watch,get=fetch):
    """Bounded exact ISIN+MIC independent reference check; no quotes or IDs logged."""
    watch_by={r["ticker"]:r for r in watch}
    wanted={}
    for m in matches:
        ticker=m["listingId"];w=watch_by.get(ticker)
        if not w:continue
        suffix=ticker.rsplit(".",1)[-1];isin=m["isin"];mic=m["mic"]
        if isin_ok(isin) and mic==MIC.get(suffix) and mic!="XHKG":
            wanted[(isin,mic)]=(ticker,CCY[suffix])
    if len(wanted)>150:raise ValueError("firds_query_budget")
    counts=Counter();checked=0;by_venue=defaultdict(Counter);keys=sorted(wanted)
    for start in range(0,len(keys),15):
        batch=keys[start:start+15]
        q=" OR ".join("(isin:"+i+" AND mic:"+m+")" for i,m in batch)
        url=FIRDS+"?"+urlencode({"q":"("+q+")","fq":"latest_received_flag:1","rows":100,"wt":"json","fl":"isin,mic,lei,gnr_full_name,gnr_cfi_code,gnr_notional_curr_code,mrkt_trdng_start_date,mrkt_trdng_trmination_date,status_label"})
        payload=json.loads(get(url));response=payload["response"];docs=response["docs"]
        if not isinstance(docs,list) or response["numFound"]!=len(docs):raise ValueError("firds_incomplete_batch")
        lookup=defaultdict(list)
        for row in docs:
            k=(row.get("isin"),row.get("mic"))
            if k not in batch:raise ValueError("firds_unexpected_identity")
            lookup[k].append(row)
        for k in batch:
            ticker,currency=wanted[k];rows=lookup[k]
            if not rows:status="not_in_register"
            elif len(rows)!=1:status="ambiguous_register_record"
            else:
                row=rows[0];cfi=row.get("gnr_cfi_code","")
                if row.get("gnr_notional_curr_code")!=currency or not isinstance(cfi,str) or not cfi.startswith("E"):
                    status="currency_or_class_mismatch"
                else:status="exact_reference_match"
            counts[status]+=1;by_venue[watch_by[ticker]["exchange"]][status]+=1;checked+=1
    return {"checked":checked,"counts":dict(counts),"byVenue":{k:dict(v) for k,v in by_venue.items()},"currentTradingStatusVerified":False,"priceCoverageVerified":False}

def crosscheck(watch,figis,items,key,mapper=None,reference_get=None):
    from exchange_identity import reconcile
    candidates,rows,counts=candidate_keys(watch,figis,items)
    result={"candidateCounts":counts,"candidateISINMICCount":len(candidates),"exactTechnicalJoins":0,"priceCoverageVerified":False}
    if not key:return {**result,"status":"missing_existing_openfigi_key"}
    if not candidates:return {**result,"status":"no_candidates"}
    if mapper is None:mapper=reconcile
    matches,summary=mapper(candidates,rows,key)
    # Only the counts are logged; source identity records are not published.
    result.update(status="checked",exactTechnicalJoins=len(matches),mappingStatus=summary)
    if reference_get is not None and matches:
        try:result["esma"]=firds_check(matches,watch,reference_get)
        except HTTPError as e:result["esma"]={"status":"http_error","httpStatus":e.code}
        except Exception as e:result["esma"]={"status":"unavailable","errorType":type(e).__name__}
    return result

def audit(watch,identities,items):
    prior={x["ticker"]:x for x in identities if x.get("ticker") and isin_ok(x.get("isin")) and x.get("evidence")}
    keys={x[:3] for x in items}
    names=defaultdict(set)
    for isin,mic,ccy,name,_ in items:
        names[(mic,ccy,name)].add(isin)
    counts=Counter();by_venue=defaultdict(Counter)
    for row in watch:
        ticker=row["ticker"];suffix=ticker.rsplit(".",1)[-1]
        mic,ccy=MIC.get(suffix),CCY.get(suffix)
        known=prior.get(ticker)
        if known:
            status="existing_isin_overlap" if (known["isin"],mic,ccy) in keys else "existing_isin_not_in_sample"
        else:
            matches=names[(mic,ccy,normalized(row["name"]))]
            status="unique_name_candidate" if len(matches)==1 else "ambiguous_name_candidate" if matches else "unresolved"
        counts[status]+=1;by_venue[row.get("exchange",suffix)][status]+=1
    return {"watchlist":len(watch),"counts":dict(counts),"byVenue":{k:dict(v) for k,v in by_venue.items()},"priceCoverageVerified":False}
def run(get=fetch):
    now=datetime.now(timezone.utc);items=set();results={};stopped=False
    for book in BOOKS:
        if stopped:break
        try:
            part,summary=reference(get(f"https://{HOST}/{book}/market_data/symbol_listing/csv/"),now)
            items.update(part);results[book]={"status":"reference_ok",**summary}
        except HTTPError as e:
            results[book]={"status":"http_error","httpStatus":e.code}
            if e.code in (401,403,429):stopped=True
        except Exception as e:results[book]={"status":"unavailable","errorType":type(e).__name__}
    watch=json.loads((ROOT/"watchlist.json").read_text())["tickers"]
    ids=json.loads((ROOT/"data/issuer-identities.json").read_text())["entities"]
    out={"books":results,"coverage":audit(watch,ids,items),"sampleComplete":len(results)==len(BOOKS) and all(v["status"]=="reference_ok" for v in results.values()),"rawTradesDownloaded":False,"publicationApproved":False}
    print("DIRECT_EXCHANGE_AUDIT "+json.dumps(out),flush=True)
    if items:
        try:
            figis=json.loads((ROOT/"data/registered-source-status.json").read_text())["figiCandidates"]
            print("DIRECT_FIGI_CROSSCHECK "+json.dumps(crosscheck(watch,figis,items,os.getenv("STOCKWATCH_OPENFIGI_KEY",""),reference_get=get)),flush=True)
        except HTTPError as e:print("DIRECT_FIGI_CROSSCHECK "+json.dumps({"status":"http_error","httpStatus":e.code}),flush=True)
        except Exception as e:print("DIRECT_FIGI_CROSSCHECK "+json.dumps({"status":"unavailable","errorType":type(e).__name__}),flush=True)
    # Inspect public landing pages only, never click agreement, fetch a
    # restricted trade file or try alternate endpoints after denial.
    for key,url in SOURCES.items():
        if key=="cboe_transparency" and stopped:continue
        try:
            content=get(url).decode("utf8",errors="replace").lower()
            print("DIRECT_PORTAL "+json.dumps({"provider":key,"status":"landing_page_reached","termsMentioned":"terms of use" in content or "disclaimer" in content,"agreementGateText":"i agree" in content,"tradeDownloadAttempted":False}),flush=True)
        except HTTPError as e:print("DIRECT_PORTAL "+json.dumps({"provider":key,"status":"http_error","httpStatus":e.code}),flush=True)
        except Exception as e:print("DIRECT_PORTAL "+json.dumps({"provider":key,"status":"unavailable","errorType":type(e).__name__}),flush=True)
if __name__=="__main__":run()
