import sys, unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalyst_evidence import build

NOW = datetime(2026,11,19,20,tzinfo=timezone.utc)
GRAPH={"schemaVersion":1,"compiledOn":"2026-11-19","entities":[{"id":"a","name":"Alpha","aliases":["Alpha"],"listingId":"XOSL:A"},{"id":"b","name":"Beta","aliases":["Beta"]}],"relationships":[{"id":"contract","from":"a","to":"b","type":"supply_contract","subject":"Equipment order","disclosedOn":"2026-11-18","reviewedOn":"2026-11-19","sourceUrl":"https://example.org/filing","sourceLocator":"Page 2","evidenceStatus":"issuer_disclosed","amount":{"value":100,"currency":"EUR","comparison":"up_to","basis":"Contract ceiling"},"actualCashFlow":False}]}
def row(**extra):
    return dict({"id":"id1","ticker":"A.OL","name":"Alpha","category":"Contracts","type":"news","match":"name_mentioned","relevance":"mentioned","url":"https://example.org/story","published":"2026-11-18T12:00:00Z","headline":"Alpha signs EUR 10 million deal"},**extra)
class CatalystTests(unittest.TestCase):
    def run_build(self, rows, seed=()):
        return build(rows,[{"ticker":"A.OL"}],seed,GRAPH,NOW)
    def test_headline_amount_not_inferred(self):
        data=self.run_build([row(),row()])
        self.assertEqual(data["counts"],{"media_lead":1,"reviewed_disclosure":1})
        lead=next(r for r in data["items"] if r["evidenceStatus"]=="media_lead")
        for field in ("amount","eventDate","counterparty","actualCashFlow","priceEffect"):
            self.assertIsNone(lead[field])
        self.assertNotIn("headline",lead)
    def test_reviewed_contract_preserves_reported_basis(self):
        reviewed=self.run_build([])["items"][0]
        self.assertEqual(reviewed["amount"]["comparison"],"up_to")
        self.assertEqual(reviewed["amount"]["basis"],"Contract ceiling")
        self.assertFalse(reviewed["actualCashFlow"])
        self.assertEqual(reviewed["counterparty"],"Beta")
    def test_unsafe_ambiguous_future_or_duplicate_excluded(self):
        data=self.run_build([row(relevance="review"),row(url="http://example.org"),row(duplicateOf="a"),row(published="2026-11-20T01:00:00Z"),row(ticker="B.OL")])
        self.assertEqual(data["counts"],{"reviewed_disclosure":1})
    def test_issuer_headline_remains_unreviewed(self):
        data=self.run_build([row(type="disclosure",match="issuer_code",relevance="strong")])
        event=next(r for r in data["items"] if r.get("newsId"))
        self.assertEqual(event["evidenceStatus"],"issuer_headline")
        self.assertIsNone(event["amount"])
    def test_sec_exact_cik_and_symbol(self):
        seed=[{"id":"XNAS:ABC","symbol":"ABC","cik":"0000000001","identityStatus":"sec_ticker_exchange_association"}]
        item=row(ticker="ABC",category="General",type="disclosure",match="issuer_code",relevance="strong",sourceFeed="sec_edgar",sourceIssuer="0000000001",form="10-Q")
        data=self.run_build([item,dict(item,id="bad",sourceIssuer="0000000002")],seed)
        leads=[r for r in data["items"] if r.get("newsId")]
        self.assertEqual(len(leads),1)
        self.assertEqual(leads[0]["listingId"],"XNAS:ABC")
        self.assertEqual(leads[0]["category"],"periodic_filing")
