"""V96 release integrity: truthful freshness, dated issuer notices and scan schedules."""
import re
from pathlib import Path
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
class V96IntegrityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overview=(ROOT/"v4.js").read_text(encoding="utf-8")
        cls.calendar=(ROOT/"research.js").read_text(encoding="utf-8")
        cls.index=(ROOT/"index.html").read_text(encoding="utf-8")
        cls.calendarhtml=(ROOT/"calendar.html").read_text(encoding="utf-8")
        cls.css=(ROOT/"freshness-v96.css").read_text(encoding="utf-8")
        cls.scan=(ROOT/".github/workflows/scan.yml").read_text(encoding="utf-8")
        cls.production=(ROOT/"scripts/production_health.py").read_text(encoding="utf-8")
    def test_overview_shows_actual_strict_session_coverage(self):
        for key in ("state.health?.priceFreshness","equities","strict?.comparable",
                    "strict?.unconfirmed","confirmed for completed session",
                    "Older moves are not live alerts",
                    "sw96-source-status"):
            self.assertIn(key,self.overview)
        self.assertIn("freshness-v96.css?v=1",self.index)
        self.assertIn("dated observations",self.overview)
    def test_calendar_source_based_releases_separate_from_future_dates(self):
        for key in ("state.archive?.items","type==='disclosure'",
                    "match==='issuer_code'","validLink(x.url)",
                    "Recently published issuer disclosures","not upcoming event dates",
                    "sw96-calendar-sync","Original issuer disclosure"):
            self.assertIn(key,self.calendar)
        self.assertIn("freshness-v96.css?v=1",self.calendarhtml)
        self.assertIn("No qualifying source-backed future events",self.calendar)
        self.assertIn("x.date>=today",self.calendar)
        self.assertIn("dateOK(x.date)",self.calendar)
        self.assertIn("Source unavailable",self.calendar)
        self.assertNotIn("Math.random(",self.calendar)
    def test_scanner_expected_weekday_and_weekend_refresh(self):
        self.assertIn('cron: "5 6-17 * * 1-5"',self.scan)
        self.assertIn('cron: "20 22 * * 1-5"',self.scan)
        self.assertIn('cron: "5 9,15 * * 0,6"',self.scan)
        self.assertIn("python scripts/build_research_data.py",self.scan)
        self.assertIn("python scripts/publish_data.py --mode scan",self.scan)
        self.assertIn("actions/deploy-pages@v5",self.scan)
    def test_production_watchdog_warns_when_expected_scans_missing(self):
        self.assertIn('market_scan_overdue',self.production)
        self.assertIn('weekend_scan_overdue',self.production)
        self.assertIn('8<=now.hour<=19',self.production)
        self.assertIn('17<=now.hour<=20',self.production)
        self.assertIn('sessionComparable',self.production)
        self.assertIn('sessionUnconfirmed',self.production)
        self.assertIn('No successful scanner snapshot within 3 hours',self.production)
    def test_bounded_styles_are_responsive_and_nonobscuring(self):
        self.assertEqual(self.css.count("{"),self.css.count("}"))
        for k in ("sw96-source-status","sw96-recent-filings","sw96-filings-context","@media(max-width:680px)"):
            self.assertIn(k,self.css)
        for phrase in ("!important","@import","display:none"):
            self.assertNotIn(phrase,self.css)
