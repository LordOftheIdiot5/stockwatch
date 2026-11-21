"""V97b: scanner diagnostic must detect calendar offsets without repricing."""
import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from venue_session_probe import bar_dates,SessionProbe

class VenueSessionProbeTests(unittest.TestCase):
    def test_utc_vs_local_date_mismatch_is_diagnostic_only(self):
        # Europe/Oslo: 23:30 UTC on Nov 19 is Nov 20 locally.
        dt=datetime(2026,11,19,23,30,tzinfo=timezone.utc)
        data={"timezone":"Europe/Oslo","bars":[{"t":dt.timestamp(),"date":"2026-11-19","close":99,"volume":100}]}
        self.assertEqual(bar_dates(data),("2026-11-19","2026-11-20","valid"))
        chosen={"ticker":"ABC.OL","date":"2026-11-20","priceStatus":"retained"}
        probe=SessionProbe("2026-11-20")
        probe.add({"ticker":"ABC.OL","exchange":"Oslo"},data,{"date":"2026-11-19"},chosen,"provider_older_session")
        p=probe.result()
        self.assertEqual(p["tracked"],1)
        self.assertEqual(p["counts"]["localDateDiffersUtc"],1)
        self.assertEqual(p["counts"]["barBeforeTarget"],1)
        self.assertEqual(p["counts"]["localDateOnTarget"],1)
        self.assertEqual(p["counts"]["retainedTargetDateDespiteOlderBar"],1)
        self.assertEqual(chosen["date"],"2026-11-20")
        self.assertEqual(data["bars"][0]["date"],"2026-11-19")
    def test_same_date_bar_not_auto_certified(self):
        d=datetime(2026,11,20,16,tzinfo=timezone.utc)
        data={"timezone":"Europe/Stockholm","bars":[{"t":d.timestamp(),"date":"2026-11-20"}]}
        p=SessionProbe("2026-11-20")
        p.add({"exchange":"Stockholm"},data,None,{"date":"2026-11-20","priceStatus":"retained"},"invalid_or_unavailable_observation")
        self.assertEqual(p.result()["counts"]["barOnTarget"],1)
        self.assertEqual(p.result()["counts"]["retainedTargetDateDespiteOlderBar"],0)
        self.assertFalse("comparable" in p.result()["counts"])
    def test_missing_timezone_and_source_failures_do_not_invent_observations(self):
        p=SessionProbe("2026-11-20")
        p.add({"exchange":"XETRA"},None,None,{"priceStatus":"unavailable"},"no_usable_chart")
        t=datetime(2026,11,20,16,tzinfo=timezone.utc).timestamp()
        p.add({"exchange":"XETRA"},{"bars":[{"t":t}],"timezone":"No/Such_Zone"},None,{"date":"2026-11-20","priceStatus":"reported"},"reported")
        x=p.result()
        self.assertEqual(x["counts"]["chartUnavailable"],1)
        self.assertEqual(x["counts"]["unknownExchangeTimezone"],1)
        self.assertEqual(x["counts"]["barOnTarget"],1)
        self.assertEqual(x["counts"]["localDateOnTarget"],0)
    def test_no_price_values_in_aggregated_schema(self):
        p=SessionProbe("2026-11-20")
        v=datetime(2026,11,20,16,tzinfo=timezone.utc).timestamp()
        p.add({"exchange":"Oslo"},{"bars":[{"t":v,"close":12345.67}],"timezone":"Europe/Oslo"},None,{"date":"2026-11-20","priceStatus":"retained"},"reported")
        self.assertNotIn("12345.67",str(p.result()))

if __name__=="__main__": unittest.main()
