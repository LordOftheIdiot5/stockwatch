import importlib.util
import pathlib
import unittest

spec=importlib.util.spec_from_file_location("roro",pathlib.Path(__file__).resolve().parent.parent/"scripts"/"collect_roro_traffic.py")
roro=importlib.util.module_from_spec(spec)
spec.loader.exec_module(roro)

class RoroTrafficTests(unittest.TestCase):
    def fixture(self):
        keys=list(roro.COUNTRIES)
        idx={"freq":{"Q":0},"unit":{"THS_T":0},"cargo":{"RO_TOT":0},"direct":{"TOTAL":0},"rep_mar":{c:i for i,c in enumerate(keys)},"time":{"2025-Q1":0,"2025-Q2":1}}
        return {"source":"ESTAT","id":roro.DIMENSIONS,"size":[1,1,1,1,len(keys),2],"dimension":{k:{"category":{"index":v}} for k,v in idx.items()},"updated":"2026-11-17","value":{"0":0,"1":10,"2":5},"status":{"1":"p"}}

    def test_source_classification_and_zero(self):
        p=self.fixture()
        rows=roro.parse_payload(p)
        self.assertEqual(rows["EU27_2020"],[{"period":"2025-Q1","value":0,"flag":None},{"period":"2025-Q2","value":10,"flag":"p"}])
        self.assertEqual(rows["NO"],[{"period":"2025-Q1","value":5,"flag":None}])
        p["dimension"]["cargo"]["category"]["index"]={"TOTAL":0}
        with self.assertRaises(ValueError):
            roro.parse_payload(p)

    def test_retain_missing_historical_observation(self):
        p=self.fixture()
        before=roro.build_dataset(p,{},"2026-11-17")
        p["value"]={"0":2}
        result=roro.build_dataset(p,before,"2026-11-18")
        eu=next(s for s in result["series"] if s["countryCode"]=="EU27_2020")
        no=next(s for s in result["series"] if s["countryCode"]=="NO")
        self.assertEqual(eu["history"][0]["value"],2)
        self.assertEqual(eu["period"],"2025-Q2")
        self.assertEqual(eu["value"],10)
        self.assertEqual(no["lastSuccessfulRefresh"],"2026-11-17")
        self.assertEqual(no["value"],5)

if __name__=="__main__":
    unittest.main()
