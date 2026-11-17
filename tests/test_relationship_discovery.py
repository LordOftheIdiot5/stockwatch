import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import relationship_discovery as d

class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.graph=json.loads((d.ROOT/d.REL).read_text(encoding="utf8"))
    def story(self,headline,**extra):
        return {"id":"test","headline":headline,"published":"2026-11-17T12:00:00Z","url":"https://example.com/test",**extra}
    def test_actual_seed(self):
        self.assertEqual(len(d.validate(self.graph)),20)
        self.assertEqual(len(self.graph["relationships"]),21)
        self.assertTrue(all(x["actualCashFlow"] is False for x in self.graph["relationships"]))
        order=next(x for x in self.graph["relationships"] if x["id"]=="singulus-spacex-line")
        self.assertEqual(order["amount"]["comparison"],"greater_than")
        self.assertEqual((order["from"],order["to"]),("singulus","spacex"))
    def test_no_headline_promotion(self):
        result=d.discover(self.graph,[self.story("SpaceX signs supply contract with Singulus")])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["entityIds"],["singulus","spacex"])
        self.assertFalse(result[0]["relationshipVerified"])
        self.assertIsNone(result[0]["amount"])
        self.assertNotIn("headline",result[0])
        self.assertEqual(d.discover(self.graph,[self.story("SpaceX and Singulus stock market discussion")]),[])
    def test_issuer_event_and_dedup(self):
        item=self.story("New contract announcement",type="disclosure",match="issuer_code",relevance="strong",ticker="WAWI.OL")
        r=d.discover(self.graph,[item,item])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["candidateType"],"issuer_event")
        self.assertEqual(r[0]["issuerTicker"],"WAWI.OL")
        self.assertEqual(r[0]["entityIds"],[])
        self.assertEqual(d.discover(self.graph,[{**item,"match":"unverified"}]),[])
    def test_headline_event_is_not_verified(self):
        item=self.story("New supply agreement",type="news",match="name_mentioned",relevance="mentioned",ticker="SIE.DE")
        result=d.discover(self.graph,[item])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["candidateType"],"headline_event")
        self.assertFalse(result[0]["relationshipVerified"])
        self.assertEqual(result[0]["entityIds"],[])
    def test_fail_closed(self):
        for update in [{"from":"unknown"},{"actualCashFlow":True},{"amount":{"value":0,"currency":"USD","comparison":"exact_reported","basis":"fake"}},{"disclosedOn":"2027-01-01"}]:
            graph=copy.deepcopy(self.graph)
            graph["relationships"][0].update(update)
            with self.assertRaises(ValueError):d.validate(graph)
if __name__=="__main__":unittest.main()
