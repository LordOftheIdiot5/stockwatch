import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from news_quality import annotate,summary
class Drivers(unittest.TestCase):
    def row(self,title,**fields):
        return {"id":title,"headline":title,"ticker":"FRO.OL","name":"Frontline","type":"news","match":"name_mentioned","published":"2026-11-18T10:00:00Z","url":"https://example.com/news",**fields}
    def test_ambiguous_mentions_retained_but_excluded(self):
        rows=annotate([self.row("Llamau warns Welsh budget risks frontline homelessness services"),self.row("Frontline PLC reports tanker rates and quarterly results"),self.row("Actor drives a Porsche",ticker="P911.DE",name="Porsche")])
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["relevance"],"review")
        self.assertEqual(rows[0]["driverTags"],[])
        self.assertEqual(rows[2]["relevance"],"review")
        self.assertEqual({r["driver"] for r in rows[1]["driverTags"]},{"numbers","prices"})
    def test_sec_forms_not_inferred(self):
        base={"ticker":"NVDA","name":"NVIDIA","type":"disclosure","match":"issuer_code","sourceFeed":"sec_edgar"}
        rows=annotate([self.row("Quarterly report (10-Q)",**base,form="10-Q",sourceAccession="a"),self.row("Current report (8-K)",**base,form="8-K",sourceAccession="b")])
        self.assertEqual(rows[0]["driverTags"][0]["basis"],"periodic SEC report")
        self.assertEqual(rows[1]["driverTags"],[])
        self.assertEqual(summary(rows)["driverClassification"]["classified"],1)
    def test_multi_topic_evidence(self):
        row=annotate([self.row("Mowi harvest volumes rise amid salmon prices and sea lice",ticker="MOWI.OL",name="Mowi")])[0]
        self.assertEqual({r["driver"] for r in row["driverTags"]},{"operations","prices","risk"})
        self.assertEqual(row["driverVersion"],1)
