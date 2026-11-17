"""Offline IEX-TP v1 / TOPS v1.6x research decoder.
Classic Ethernet IPv4 UDP PCAP only. Output is venue-local observed bars,
not consolidated prices, official closes, or verified full-session coverage.
"""
from __future__ import annotations
import argparse
import gzip
import json
import sqlite3
import struct
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from free_research import ROOT

TERMS = "https://www.iex.io/legal/hist-data-terms"
ATTRIBUTION = "Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use."
NY = ZoneInfo("America/New_York")

def read_exact(f, n):
    b = f.read(n)
    if len(b) != n:
        raise ValueError("truncated PCAP")
    return b

def packets(f):
    h = read_exact(f, 24)
    endian = {b"\xd4\xc3\xb2\xa1":"<", b"\x4d\x3c\xb2\xa1":"<",
              b"\xa1\xb2\xc3\xd4":">", b"\xa1\xb2\x3c\x4d":">"}.get(h[:4])
    if endian is None:
        raise ValueError("unsupported PCAP format")
    major, minor = struct.unpack_from(endian+"HH", h, 4)
    if (major, minor) != (2, 4) or struct.unpack_from(endian+"I", h, 20)[0] != 1:
        raise ValueError("Ethernet PCAP v2.4 required")
    while True:
        ph = f.read(16)
        if not ph:
            return
        if len(ph) != 16:
            raise ValueError("truncated packet header")
        _, _, cap, original = struct.unpack(endian+"IIII", ph)
        if cap != original or not 14 <= cap <= 262144:
            raise ValueError("invalid or truncated packet")
        b = read_exact(f, cap)
        off = 14
        eth = int.from_bytes(b[12:14], "big")
        while eth in (0x8100, 0x88a8):
            if len(b) < off+4:
                raise ValueError("truncated VLAN")
            eth = int.from_bytes(b[off+2:off+4], "big")
            off += 4
        if eth != 0x0800:
            continue
        if len(b) < off+20 or b[off] >> 4 != 4:
            raise ValueError("invalid IPv4")
        ihl = (b[off] & 15)*4
        total = int.from_bytes(b[off+2:off+4], "big")
        if ihl < 20 or total < ihl or off+total > len(b):
            raise ValueError("invalid IPv4 length")
        if b[off+9] != 17:
            continue
        if int.from_bytes(b[off+6:off+8], "big") & 0x3fff:
            raise ValueError("fragmented UDP unsupported")
        u = off+ihl
        if total < ihl+8:
            raise ValueError("truncated UDP")
        length = int.from_bytes(b[u+4:u+6], "big")
        if length < 8 or length != total-ihl:
            raise ValueError("invalid UDP length")
        yield b[u+8:u+length]

def decode_segment(b):
    if len(b) < 40:
        raise ValueError("short IEX header")
    version, reserved, proto, channel, session, length, count, offset, seq, sent = struct.unpack_from("<BBHIIHHqqq", b)
    if version != 1 or proto != 0x8003 or channel != 1 or reserved != 0:
        raise ValueError("unsupported IEX protocol/channel")
    if length != len(b)-40 or offset < 0 or seq < 1:
        raise ValueError("invalid IEX framing")
    pos = 40
    messages = []
    for _ in range(count):
        if pos+2 > len(b):
            raise ValueError("missing message length")
        n = struct.unpack_from("<H", b, pos)[0]
        pos += 2
        if n < 1 or pos+n > len(b):
            raise ValueError("invalid message length")
        messages.append(b[pos:pos+n])
        pos += n
    if pos != len(b):
        raise ValueError("unexpected trailing payload")
    return session, seq, messages

def trade(m):
    if m[:1] not in (b"T", b"B"):
        return None
    if len(m) < 38:
        raise ValueError("short trade message")
    typ, flags, t, sym, size, price, ident = struct.unpack_from("<cBq8sIqq", m)
    symbol = sym.decode("ascii").rstrip(" ")
    if not symbol or size <= 0 or price <= 0 or ident < 0 or t <= 0:
        raise ValueError("invalid trade fields")
    if flags & 7:
        raise ValueError("unknown trade flag")
    return typ, flags, t, symbol, size, price, ident

def aggregate(payloads, day, db):
    db.execute("CREATE TABLE trades(id INTEGER PRIMARY KEY, seq INTEGER, ts INTEGER, symbol TEXT, size INTEGER, price INTEGER, flags INTEGER, broken INTEGER DEFAULT 0)")
    state = None
    next_seq = None
    message_count = 0
    for payload in payloads:
        session, seq, messages = decode_segment(payload)
        if state is None:
            state = session
            next_seq = seq
        if session != state:
            raise ValueError("multiple sessions unsupported")
        if not messages:
            continue
        if seq > next_seq:
            raise ValueError("IEX sequence gap")
        for i, m in enumerate(messages):
            s = seq+i
            if s < next_seq:
                continue
            next_seq = s+1
            message_count += 1
            row = trade(m)
            if row is None:
                continue
            typ, flags, ts, symbol, size, price, ident = row
            if datetime.fromtimestamp(ts//1_000_000_000, NY).date().isoformat() != day:
                raise ValueError("trade outside requested session date")
            if typ == b"T":
                db.execute("INSERT INTO trades(id,seq,ts,symbol,size,price,flags) VALUES(?,?,?,?,?,?,?)",
                           (ident,s,ts,symbol,size,price,flags))
            else:
                cur = db.execute("UPDATE trades SET broken=1 WHERE id=? AND symbol=? AND size=? AND price=? AND broken=0",
                                 (ident,symbol,size,price))
                if cur.rowcount != 1:
                    raise ValueError("unmatched or inconsistent trade break")
    if not message_count:
        raise ValueError("no messages")
    db.commit()
    db.execute("CREATE INDEX trade_order ON trades(symbol,ts,seq)")
    bars = {}
    # Volume includes regular-session odd lots; price bars exclude odd lots.
    for symbol, size, price, flags in db.execute(
            "SELECT symbol,size,price,flags FROM trades WHERE broken=0 AND (flags & 64)=0 ORDER BY symbol,ts,seq"):
        bar = bars.setdefault(symbol, {"symbol":symbol,"volume":0,"eligibleTrades":0,
                                       "open":None,"high":None,"low":None,"close":None})
        bar["volume"] += size
        if flags & 32:
            continue
        if bar["open"] is None:
            bar.update(open=price,high=price,low=price)
        bar["high"] = max(bar["high"], price)
        bar["low"] = min(bar["low"], price)
        bar["close"] = price
        bar["eligibleTrades"] += 1
    return {"schemaVersion":1,"date":day,"venueMic":"IEXG","currency":"USD","priceScale":10000,
            "source":"IEX HIST TOPS","scope":"observed regular session venue trades",
            "sessionCompletenessVerified":False,"consolidated":False,"officialClose":False,
            "pricePublicationAllowed":False,"corporateActionAdjusted":False,
            "attribution":ATTRIBUTION,"terms":TERMS,"messagesProcessed":message_count,
            "records":list(bars.values())}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pcap", required=True, type=Path)
    p.add_argument("--date", required=True)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--accept-iex-hist-terms", action="store_true")
    a = p.parse_args()
    if not a.accept_iex_hist_terms:
        raise PermissionError("review and accept IEX HIST terms before processing")
    if datetime.strptime(a.date,"%Y-%m-%d").date().isoformat() != a.date:
        raise ValueError("invalid date")
    out = a.output.expanduser().resolve()
    if out == ROOT or ROOT in out.parents or out == a.pcap.resolve():
        raise ValueError("private output path outside repository required")
    out.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if a.pcap.suffix == ".gz" else open
    with tempfile.TemporaryDirectory(dir=out.parent) as work:
        with sqlite3.connect(str(Path(work)/"trades.sqlite")) as db, opener(a.pcap,"rb") as f:
            result = aggregate(packets(f), a.date, db)
    tmp = out.with_suffix(out.suffix+".tmp")
    tmp.write_text(json.dumps(result,allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(out)
    print(json.dumps({"observedSymbols":len(result["records"]),"sessionCompletenessVerified":False,"pricePublicationAllowed":False}))

if __name__ == "__main__":
    main()
