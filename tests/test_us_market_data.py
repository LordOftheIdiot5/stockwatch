import io
import sqlite3
import struct
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import us_sec_directory as sec
import iex_hist_research as iex

DAY="2026-11-16"
TS=int(datetime(2026,11,16,15,tzinfo=timezone.utc).timestamp())*10**9
DIR={"fields":["cik","name","ticker","exchange"],"data":[[123,"Example","EXA","NYSE"],[123,"Example","EXB","NYSE"],[456,"Other","OTH",None]]}

def msg(typ=b"T", flags=0, ident=1, size=100, price=100000, ts=TS):
    return struct.pack("<cBq8sIqq",typ,flags,ts,b"EXA     ",size,price,ident)

def segment(seq,*messages):
    payload=b"".join(struct.pack("<H",len(m))+m for m in messages)
    return struct.pack("<BBHIIHHqqq",1,0,0x8003,1,1,len(payload),len(messages),0,seq,TS)+payload

def bar(*payloads):
    with sqlite3.connect(":memory:") as db:
        return iex.aggregate(payloads,DAY,db)

class USMarketTests(unittest.TestCase):
    def test_sec_share_classes_retained(self):
        rows=sec.normalize_directory(DIR)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["cik"],"0000000123")
        self.assertEqual(rows[1]["symbol"],"EXB")
        self.assertTrue(all(not r["priceAvailable"] for r in rows))

    def test_sec_duplicate_collapses_and_conflict_fails(self):
        rows=sec.normalize_directory({**DIR,"data":DIR["data"]+[DIR["data"][0]]})
        self.assertEqual(len(rows),3)
        with self.assertRaises(ValueError):
            sec.normalize_directory({**DIR,"data":DIR["data"]+[[123,"Conflicting","EXA","NYSE"]]})

    def test_sec_directory_only(self):
        calls=[]
        out=sec.collect(lambda u,a:(calls.append(u) or DIR),"Example contact@example.com",sleep=lambda s:None)
        self.assertEqual(calls,[sec.DIRECTORY])
        self.assertEqual(len(out["listings"]),3)
        self.assertFalse(out["pricePublicationAllowed"])

    def test_sec_batch_dedup_and_fail_closed(self):
        calls=[]
        def get(u,a):
            calls.append(u)
            if u==sec.DIRECTORY:return DIR
            raise ValueError("unavailable")
        out=sec.collect(get,"Example contact@example.com",["EXA","EXB","OTH"],sleep=lambda s:None)
        self.assertEqual(out["selectedIssuerCount"],2)
        self.assertEqual(len(calls),2)
        self.assertEqual(out["unattemptedIssuerCount"],1)
        self.assertEqual(len(out["failures"]),1)

    def test_trade_break_and_odd_lot(self):
        out=bar(segment(1,msg(ident=1),msg(ident=2,price=120000,ts=TS+1),
                        msg(ident=3,flags=32,size=3,price=200000,ts=TS+2),
                        msg(ident=4,flags=64,price=500000,ts=TS+3),
                        msg(b"B",ident=2,price=120000,ts=TS+4)))
        r=out["records"][0]
        self.assertEqual((r["open"],r["high"],r["low"],r["close"],r["volume"]),(100000,100000,100000,100000,103))
        self.assertFalse(out["consolidated"])
        self.assertFalse(out["sessionCompletenessVerified"])

    def test_duplicate_segment_and_gap(self):
        s=segment(1,msg())
        self.assertEqual(bar(s,s)["records"][0]["volume"],100)
        with self.assertRaises(ValueError):bar(s,segment(3,msg(ident=2)))

    def test_wrong_day_or_break(self):
        with self.assertRaises(ValueError):bar(segment(1,msg(ts=TS-86400*10**9)))
        with self.assertRaises(ValueError):bar(segment(1,msg(b"B",ident=20)))

    def test_truncated_message(self):
        with self.assertRaises(ValueError):iex.decode_segment(segment(1,msg())[:-1])

    def test_pcap_packet(self):
        payload=segment(1,msg())
        udp=struct.pack(">HHHH",100,100,len(payload)+8,0)+payload
        ip=bytearray(20)
        ip[0]=0x45
        ip[2:4]=struct.pack(">H",20+len(udp))
        ip[9]=17
        frame=b"\0"*12+b"\x08\x00"+ip+udp
        header=struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,65535,1)
        packet=struct.pack("<IIII",0,0,len(frame),len(frame))+frame
        self.assertEqual(list(iex.packets(io.BytesIO(header+packet))),[payload])

if __name__=="__main__":
    unittest.main()
