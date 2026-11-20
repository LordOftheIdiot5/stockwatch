"""Taiwan official openly licensed daily securities observations; independent from scanner."""
import argparse,hashlib,json,os,re
from datetime import date,datetime,timezone
from decimal import Decimal
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

URL="https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
SOURCE="https://data.gov.tw/en/datasets/11549"
LICENSE="https://data.gov.tw/en/license"
ATTRIBUTION="Financial Supervisory Commission / Securities and Futures Bureau, Taiwan Stock Exchange, Stock daily transaction information (dataset 11549), Open Government Data License v1.0; normalized by Nordl."
FIELDS={"Date","Code","Name","TradeVolume","TradeValue","OpeningPrice","HighestPrice","LowestPrice","ClosingPrice","Change","Transaction"}
def number(x,integer=False,nullable=False):
    if not isinstance(x,str):raise ValueError("unexpected number type")
    s=x.strip().replace(",","")
    if nullable and s in ("","--","---","N/A"):return None
    if not re.fullmatch(r"\d+" if integer else r"\d+(\.\d+)?",s) or len(s)>30:raise ValueError("unexpected numeric field")
    return int(s) if integer else str(Decimal(s))
def parse(data,today):
    if not isinstance(data,list) or not 1<=len(data)<=10000:raise ValueError("payload bound")
    days=set();seen=set();rows=[]
    for r in data:
        if not isinstance(r,dict) or not FIELDS<=set(r):raise ValueError("unexpected schema")
        d=r["Date"]
        if not isinstance(d,str) or not re.fullmatch(r"\d{7}",d):raise ValueError("unexpected ROC session date")
        day=date(int(d[:3])+1911,int(d[3:5]),int(d[5:]))
        if day>today or (today-day).days>14 or day.weekday()>=5:raise ValueError("invalid source date")
        days.add(day.isoformat())
        code=r["Code"]
        if not isinstance(code,str) or not re.fullmatch("[0-9A-Z]{2,12}",code) or code in seen:raise ValueError("invalid or duplicate security code")
        seen.add(code)
        name=r["Name"]
        if not isinstance(name,str) or not name.strip() or len(name)>150:raise ValueError("invalid name")
        o,h,l,c=[number(r[k],nullable=True) for k in ("OpeningPrice","HighestPrice","LowestPrice","ClosingPrice")]
        v=number(r["TradeVolume"],integer=True)
        if all(x is not None for x in (o,h,l,c)):
            if min(map(Decimal,(o,h,l,c)))<=0 or not Decimal(l)<=min(Decimal(o),Decimal(c))<=max(Decimal(o),Decimal(c))<=Decimal(h):raise ValueError("invalid OHLC")
        status="reported" if v>0 and all(x is not None for x in (o,h,l,c)) else "no_volume" if v==0 else "incomplete"
        rows.append({"securityId":"XTAI:"+code,"code":code,"name":name,"currency":"TWD","date":day.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v,"tradeValue":number(r["TradeValue"],integer=True),"tradeCount":number(r["Transaction"],integer=True),"status":status})
    if len(days)!=1:raise ValueError("mixed trading sessions")
    if not any(x["status"]=="reported" for x in rows):raise ValueError("no traded observations")
    return {"schemaVersion":1,"sourceUrl":SOURCE,"endpoint":URL,"licenseUrl":LICENSE,"attribution":ATTRIBUTION,"market":"XTAI","sessionDate":next(iter(days)),"records":sorted(rows,key=lambda r:r["code"]),"notice":"Official reported daily securities observations, not necessarily ordinary shares; no cross-listing substitution, adjustment or inferred price."}
def fetch():
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"application/json"}),timeout=45) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(16*1024**2+1)
    if len(raw)>16*1024**2:raise ValueError("response bound")
    return raw
def encode(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def archive(client,data,source):
    from private_r2_archive import BUCKET,immutable_put
    body=encode(data);day=data["sessionDate"]
    key=f"open-equity/v1/xtai/{day}/{sha(body)}.json"
    def put(k,b):
        state=immutable_put(client,b,k,{"dataset":"twse-stock-day","sha256":sha(b)},"application/json")
        stream=client.get_object(Bucket=BUCKET,Key=k)["Body"]
        try:actual=stream.read(len(b)+1)
        finally:stream.close()
        if len(actual)!=len(b) or sha(actual)!=sha(b):raise ValueError("R2 readback mismatch")
        return state
    state=put(key,body)
    receipt=encode({"sourceUrl":SOURCE,"endpoint":URL,"licenseUrl":LICENSE,"sourceSha256":sha(source),"objectSha256":sha(body),"objectKey":key,"records":len(data["records"]),"sessionDate":day,"status":"readback_verified"})
    receipt_key=f"open-equity/v1/xtai/receipts/{sha(receipt)}.json"
    put(receipt_key,receipt)
    return {"storageStatus":state,"receiptKey":receipt_key,"readbackVerified":True}
def main():
    p=argparse.ArgumentParser();p.add_argument("--retain-private",action="store_true");args=p.parse_args()
    raw=fetch();data=parse(json.loads(raw),datetime.now(ZoneInfo("Asia/Taipei")).date())
    stats={"sessionDate":data["sessionDate"],"rows":len(data["records"]),"reported":sum(r["status"]=="reported" for r in data["records"]),"sourceSha256":sha(raw),"readbackVerified":False}
    if args.retain_private:
        if os.environ.get("STOCKWATCH_TWSE_PRIVATE_RETENTION")!="true":raise ValueError("retention not enabled")
        from private_r2_archive import configuration
        from botocore.config import Config
        import boto3
        account=configuration(os.environ,smoke_only=True)
        client=boto3.client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["STOCKWATCH_R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["STOCKWATCH_R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",connect_timeout=15,read_timeout=60,retries={"max_attempts":3}))
        stats.update(archive(client,data,raw))
    print("TWSE_EQUITY_PILOT "+json.dumps(stats,sort_keys=True))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("TWSE_EQUITY_FAILED "+type(exc).__name__+(" "+str(exc) if isinstance(exc,ValueError) and str(exc) in {"unexpected number type","unexpected numeric field","payload bound","unexpected schema","unexpected ROC session date","invalid source date","invalid or duplicate security code","invalid name","invalid OHLC","mixed trading sessions","no traded observations","unexpected redirect","response bound"} else ""))
        raise SystemExit(1) from None
