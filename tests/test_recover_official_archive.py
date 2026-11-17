import copy
import datetime as dt
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
import recover_official_archive as recovery

class RecoveryTests(unittest.TestCase):
    def test_preserve_newer_values_and_restore_empty_series(self):
        path=recovery.ROOT/"data"/"shipping-connectivity.json"
        original=json.loads(path.read_text())
        archived=recovery.validate("unctad-connectivity",original)
        current=copy.deepcopy(original)
        current["series"][0]["value"]=12345
        current["series"][1]["history"]=[]
        current["series"].pop(2)
        out,count=recovery.recover("unctad-connectivity",current,archived,"2026-11-17")
        self.assertEqual(count,2)
        self.assertEqual(out["series"][0],current["series"][0])
        self.assertEqual(out["series"][1]["period"],archived["series"][1]["period"])
        self.assertEqual(out["series"][1]["archiveRecovery"]["status"],"retained")
        self.assertEqual(out["source"]["status"],"retained")
        self.assertEqual(len(out["series"]),len(original["series"]))

    def test_never_use_other_currency_or_wrong_kind_or_private_quotes(self):
        archived=recovery.validate("official-fx-macro",json.loads((recovery.ROOT/"data"/"open-data.json").read_text()))
        row=archived["series"][0]
        current={"series":[{**row,"unit":"different unit","history":[]}]}
        out,count=recovery.recover("official-fx-macro",current,{"series":[row]},"2026-11-17")
        self.assertEqual(count,0)
        self.assertEqual(out,current)
        self.assertEqual(recovery.recover("official-fx-macro",None,archived,"2026-11-17"),(None,0))
        with self.assertRaises(ValueError):
            recovery.latest_snapshot(Mock(),"scanner-observations",dt.datetime.now(dt.timezone.utc))

    def test_integrity_gate(self):
        data=json.loads((recovery.ROOT/"data"/"shipping-roro-traffic.json").read_text())
        raw=json.dumps(data).encode()
        digest=hashlib.sha256(raw).hexdigest()
        now=dt.datetime(2026,11,17,tzinfo=dt.timezone.utc)
        item={"Key":f"observations/eurostat-roro/2026-11-17/{digest}.json","Size":len(raw),"LastModified":now}
        client=Mock()
        client.get_paginator.return_value.paginate.return_value=[{"Contents":[item]}]
        client.get_object.return_value={"Body":io.BytesIO(raw),"Metadata":{"sha256":digest}}
        result,day=recovery.latest_snapshot(client,"eurostat-roro",now)
        self.assertEqual(day,"2026-11-17")
        self.assertEqual(len(result["series"]),10)
        client.get_object.side_effect=lambda **kwargs:{"Body":io.BytesIO(b"invalid"),"Metadata":{"sha256":digest}}
        self.assertEqual(recovery.latest_snapshot(client,"eurostat-roro",now),(None,None))

    def test_unchanged_complete_series(self):
        for kind,filename in recovery.FILES.items():
            with self.subTest(kind=kind):
                current=json.loads((recovery.ROOT/"data"/filename).read_text())
                out,count=recovery.recover(kind,current,recovery.validate(kind,current),"2026-11-17")
                self.assertEqual(count,0)
                self.assertEqual(out,current)
if __name__=="__main__":
    unittest.main()
