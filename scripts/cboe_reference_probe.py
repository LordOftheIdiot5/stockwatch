"""Cboe standard symbol CSV schema and exact ISIN/MIC coverage probe.
No price values, restricted RIC fields, vendor files or individual reference rows persisted.
"""
import csv, io, json, re
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from exchange_identity import valid_isin
ROOT=Path(__file__).resolve().parents[1]
URL="https://accounteu.cboe.com/cxe/market_data/symbol_listing/csv/"
LIMIT=16*1024*1024
def inspect(raw,expected):
    stream=io.StringIO(raw.decode("utf-8-sig"),newline="")
    descriptor=next(csv.reader([stream.readline()]))
    desc=dict(x.split("=",1) for x in descriptor if "=" in x)
    if desc.get("environment")!="PROD" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",desc.get("created","")):raise ValueError("invalid production descriptor")
    reader=csv.DictReader(stream)
    required={"isin","mic","currency","live","asset_class"}
    if not required.issubset(reader.fieldnames or []) or len(reader.fieldnames)!=len(set(reader.fieldnames)):raise ValueError("unexpected schema")
    eligible=set();rows=0;venues=set()
    for r in reader:
        rows+=1
        if None in r or any(v is None for v in r.values()):raise ValueError("malformed row")
        if r["live"]!="t" or r["asset_class"]!="EQTY" or not valid_isin(r["isin"]) or not re.fullmatch(r"[A-Z0-9]{4}",r["mic"]):continue
        eligible.add((r["isin"],r["mic"]));venues.add(r["mic"])
    return {"fileDate":desc["created"],"warningPresent":bool(desc.get("warning")),"rawRowCount":rows,"uniqueLiveEquityIdentities":len(eligible),"primaryMICCount":len(venues),"knownExactISINMICMatches":len(eligible&expected),"knownExactISINMICInputs":len(expected),"pricesCollected":False,"rawRowsPersisted":False}
def main():
    targets=json.loads((ROOT/"data/research-targets.json").read_text())["targets"]
    expected={(r["isin"],r["mic"]) for r in targets if r.get("isin") and valid_isin(r["isin"]) and r.get("mic")}
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Research (https://stocks.nordl.dev/; vidar@nordl.dev)","Accept":"text/csv"}),timeout=30) as res:
        if res.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=res.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError("size limit")
    print("CBOE_REFERENCE "+json.dumps(inspect(raw,expected),sort_keys=True))
if __name__=="__main__":main()
