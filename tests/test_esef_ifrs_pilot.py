import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esef_ifrs_pilot import extract,json_path,cohort
from test_esef_filing_index import fixture,LEI

NS={"i":"http://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full","l":"http://standards.iso.org/iso/17442","u":"http://www.xbrl.org/2003/iso4217","fake":"https://example.org/ifrs-full"}
def fact(name="Revenue",period="2025-01-01T00:00:00/2026-01-01T00:00:00",value="1000"):
    return {"value":value,"decimals":-3,"dimensions":{"concept":"i:"+name,"entity":"l:"+LEI,"period":period,"unit":"u:NOK"}}
def report(facts):return {"documentInfo":{"documentType":"https://xbrl.org/2021/xbrl-json","namespaces":NS},"facts":facts}
class Tests(unittest.TestCase):
    def test_exact_annual_and_instant(self):
        out,_=extract(report({"r":fact(),"a":fact("Assets","2026-01-01T00:00:00")}),LEI,"2025-12-31")
        self.assertEqual(set(out),{"Revenue","Assets"});self.assertEqual(out["Revenue"]["currency"],"NOK")
        self.assertEqual(out["Revenue"]["value"],"1000")
    def test_wrong_taxonomy_entity_currency_dimension_period(self):
        a=fact();a["dimensions"]["concept"]="fake:Revenue"
        b=fact();b["dimensions"]["entity"]="l:other"
        c=fact();c["dimensions"]["unit"]="u:NOK/u:USD"
        d=fact();d["dimensions"]["i:SegmentAxis"]="i:Segment"
        e=fact(period="2025-10-01T00:00:00/2026-01-01T00:00:00")
        out,counts=extract(report(dict(a=a,b=b,c=c,d=d,e=e)),LEI,"2025-12-31")
        self.assertEqual(out,{});self.assertEqual(sum(counts.values()),4)
    def test_conflicting_duplicates_withheld(self):
        out,counts=extract(report({"a":fact(),"b":fact(value="2000")}),LEI,"2025-12-31")
        self.assertEqual(out,{});self.assertEqual(counts["conflictingConcepts"],1)
    def test_identical_duplicates(self):
        a=fact();out,_=extract(report({"b":a,"a":copy.deepcopy(a)}),LEI,"2025-12-31")
        self.assertEqual(out["Revenue"]["factId"],"a")
    def test_invalid_amount_and_wrong_end(self):
        out,_=extract(report({"a":fact(value="NaN"),"b":fact("Assets","2025-12-31T00:00:00")}),LEI,"2025-12-31")
        self.assertEqual(out,{})
    def test_pilot_path_and_cohort(self):
        for p in ("//bad.org/x.json","/../x.json","/%2e%2e/x.json","/x.json?foo=bar","https://bad.org/x.json"):self.assertIsNone(json_path(p))
        d=fixture();out=cohort(d,{LEI:{"MOWI"}})
        self.assertEqual(len(out),1);self.assertEqual(out[0]["url"],"https://filings.xbrl.org/example.json")
        d["data"][0]["attributes"]["error_count"]=1
        self.assertEqual(cohort(d,{LEI:{"MOWI"}}),[])
