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
        self.assertEqual(len(d.validate(self.graph)),40)
        self.assertEqual(len(self.graph["relationships"]),34)
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
    def test_review_identity_survives_new_aliases_and_missing_source(self):
        item=self.story("SpaceX signs supply contract with Singulus",ticker="SIE.DE",match="name_mentioned",relevance="mentioned")
        initial=d.discover(self.graph,[item])[0]
        prior=d.merge_review([], [initial],self.graph,"2026-11-18T00:00:00Z")
        changed={**initial,"entityIds":["spacex"],"candidateType":"headline_event"}
        current=d.merge_review(prior,[changed],self.graph,"2026-11-18T01:00:00Z")
        self.assertEqual(current[0]["id"],prior[0]["id"])
        self.assertEqual(current[0]["firstSeenAt"],"2026-11-18T00:00:00Z")
        self.assertEqual(current[0]["lastSeenAt"],"2026-11-18T01:00:00Z")
        self.assertEqual(current[0]["entityIds"],["singulus","spacex"])
        retained=d.merge_review(current,[],self.graph,"2026-11-18T02:00:00Z")
        self.assertEqual(len(retained),1)
        self.assertFalse(retained[0]["currentlyDetected"])
        self.assertFalse(retained[0]["relationshipVerified"])
        self.assertEqual(retained[0]["lastSeenAt"],"2026-11-18T01:00:00Z")

    def test_related_evidence_across_duplicate_news_ids(self):
        graph=copy.deepcopy(self.graph)
        graph["relationships"][0]["discoveryNewsId"]="other"
        item=self.story("SpaceX signs supply contract with Singulus",ticker="SIE.DE",match="name_mentioned",relevance="mentioned")
        rows=d.discover(graph,[item,{**item,"id":"other"}])
        self.assertEqual(len(rows),1)
        result=d.merge_review([],rows,graph,"2026-11-18T00:00:00Z")
        self.assertEqual(result[0]["newsIds"],["other","test"])
        self.assertEqual(result[0]["relatedRelationshipIds"],[graph["relationships"][0]["id"]])
        self.assertEqual(result[0]["status"],"related_evidence_recorded")
        self.assertFalse(result[0]["relationshipVerified"])

    def test_fail_closed(self):
        for update in [{"from":"unknown"},{"actualCashFlow":True},{"amount":{"value":0,"currency":"USD","comparison":"exact_reported","basis":"fake"}},{"disclosedOn":"2027-01-01"}]:
            graph=copy.deepcopy(self.graph)
            graph["relationships"][0].update(update)
            with self.assertRaises(ValueError):d.validate(graph)
if __name__=="__main__":unittest.main()
