"""Validate FIRDS daily change-set completeness and actual delta action structure.
This is a read-only probe, not historical replay or an updated security master.
"""
from __future__ import annotations
import json,tempfile,zipfile
from collections import Counter
from datetime import datetime,timezone,date,timedelta
from pathlib import Path
from defusedxml.ElementTree import iterparse
from esma_firds_preflight import discover,manifest
from esma_equity_extract import download,MAX_XML

NS="{urn:iso:std:iso:20022:tech:xsd:auth.036.001.03}"
REPORT=NS+"FinInstrmRptgRefDataDltaRpt"
ACTIONS={NS+x:x for x in ("NewRcrd","ModfdRcrd","TermntdRcrd","CancRcrd")}
DOCS="https://www.esma.europa.eu/document/firds-instructions-access-and-download-full-and-delta-reference-data-files"

def select(groups,today):
    full=[g for g in groups if g["type"]=="FULINS_E" and date.fromisoformat(g["date"])<=today]
    if not full:raise ValueError("missing weekly baseline")
    baseline=max(full,key=lambda g:g["date"])
    if not baseline["complete"]:raise ValueError("incomplete latest baseline")
    start=date.fromisoformat(baseline["date"])
    days={date.fromisoformat(g["date"]):g for g in groups if g["type"]=="DLTINS" and start<date.fromisoformat(g["date"])<=today}
    # Do not pretend that the newest publication date has finished when no file exists yet.
    if not days:raise ValueError("no delta after baseline")
    latest=max(days);expected=[start+timedelta(days=i) for i in range(1,(latest-start).days+1)]
    if any(d not in days or not days[d]["complete"] for d in expected):raise ValueError("missing or incomplete daily delta set")
    group=days[latest]
    if not 1<=len(group["files"])<=16 or len(group["files"])!=group["expectedParts"]:raise ValueError("unbounded or incomplete latest delta")
    return baseline,expected,group

def inspect(stream):
    stack=[];counts=Counter();layouts={};report_count=0
    def paths(el,prefix="",depth=0):
        if depth>12:raise ValueError("unexpected record nesting")
        local=el.tag.split("}",1)[-1]
        here=prefix+"/"+local
        result={here}
        for child in el:result.update(paths(child,here,depth+1))
        return result
    for event,el in iterparse(stream,events=("start","end"),forbid_dtd=True,forbid_entities=True,forbid_external=True):
        if event=="start":
            stack.append(el)
            if len(stack)>64:raise ValueError("unexpected XML depth")
            if el.tag==REPORT:report_count+=1
            continue
        if el.tag==NS+"FinInstrm" and len(stack)>1 and stack[-2].tag==REPORT:
            if len(el)!=1 or el[0].tag not in ACTIONS:raise ValueError("unknown delta action")
            action=ACTIONS[el[0].tag];counts[action]+=1
            # Record field paths, not raw instrument or issuer values.
            if action not in layouts:layouts[action]=sorted(paths(el[0]))
            stack[-2].remove(el);el.clear()
        stack.pop()
    if report_count!=1:raise ValueError("missing or ambiguous delta report")
    return {"actionCounts":dict(counts),"firstRecordFieldPaths":layouts}

def inspect_archive(path):
    with zipfile.ZipFile(path) as z:
        files=[i for i in z.infolist() if not i.is_dir()]
        if len(files)!=1 or not files[0].filename.lower().endswith(".xml") or not 0<files[0].file_size<=MAX_XML:raise ValueError("invalid XML archive")
        with z.open(files[0]) as stream:return inspect(stream)

def run(now=None):
    now=now or datetime.now(timezone.utc);today=now.date()
    groups=manifest(discover(today-timedelta(days=13),today))
    baseline,days,latest=select(groups,today)
    parts=[];counts=Counter()
    with tempfile.TemporaryDirectory() as temp:
        for f in latest["files"]:
            path=Path(temp)/"delta.zip";digest=download(f,path);data=inspect_archive(path)
            counts.update(data["actionCounts"])
            parts.append({"file":f["name"],"url":f["url"],**digest,**data})
            path.unlink()
    out={"baselineDate":baseline["date"],"manifestCompleteThrough":latest["date"],"manifestDays":len(days),"downloadedDeltaDate":latest["date"],"parts":parts,"actionCounts":dict(counts),
         "currentStateEstablished":False,"replayComplete":False,"sourceUrl":DOCS,"notice":"Only latest discovered complete delta day downloaded. Manifest completeness does not establish applied historical replay. No instrument values stored."}
    print("ESMA_DELTA_PREFLIGHT "+json.dumps(out,sort_keys=True));return out
if __name__=="__main__":run()
