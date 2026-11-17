import csv,io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import exchange_profile_audit as a
import delayed_exchange as ex
def fixture():
    fields=sorted(ex.REQUIRED)+["MmtFlags","CorrectionFlag"]
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader()
    row={k:"private-value" for k in fields}
    row["CorrectionFlag"]=""
    w.writerow(row)
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr("trades.csv",s.getvalue())
    return b.getvalue()
class ProfileAuditTests(unittest.TestCase):
    def test_condition_field_coverage_without_raw_values(self):
        r=a.inspect(fixture())
        self.assertEqual(r["reportRowCount"],1)
        self.assertEqual(r["conditionCoverage"]["MmtFlags"],{"populated":1})
        self.assertEqual(r["conditionCoverage"]["CorrectionFlag"],{"empty":1})
        self.assertFalse(r["officialCloseVerified"])
        self.assertFalse(r["pricePublicationAllowed"])
        self.assertNotIn("private-value",str(r))
    def test_invalid_report_rejected(self):
        with self.assertRaises(zipfile.BadZipFile):a.inspect(b"not a zip")

    def test_quality_aggregate_without_numeric_payload(self):
        fields=sorted(ex.REQUIRED)+["MifidPriceNotation","MissingPrice","MmtModificationIndicator","MmtContributionToPrice"]
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader()
        row={k:"private-value" for k in fields}
        row.update(MifidPrice="9876.54321",MifidQuantity="1",MifidPriceNotation="MONE",MissingPrice="",MmtModificationIndicator="-",MmtContributionToPrice="P")
        w.writerow(row);w.writerow({**row,"MifidPrice":"NaN","MmtModificationIndicator":"CANC","MifidPriceNotation":"UNREVIEWED"})
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:z.writestr("trades.csv",s.getvalue())
        out=a.inspect(b.getvalue())
        self.assertTrue(out["reviewFieldsPresent"])
        self.assertEqual(out["numericQualityCounts"]["positive_finite_price"],1)
        self.assertEqual(out["numericQualityCounts"]["invalid_price"],1)
        self.assertEqual(out["modificationCounts"]["CANC"],1)
        self.assertEqual(out["priceNotationCounts"]["other"],1)
        self.assertNotIn("9876.54321",str(out))
        self.assertNotIn("private-value",str(out))
        self.assertNotIn("UNREVIEWED",str(out))
