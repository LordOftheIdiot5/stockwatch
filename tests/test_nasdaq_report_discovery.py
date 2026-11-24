import sys,unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from nasdaq_report_discovery import inspect
NOW=datetime(2026,11,20,2,tzinfo=timezone.utc)
def page(*links):return "".join('<a href="'+x+'">file</a>' for x in links).encode()
class Tests(unittest.TestCase):
    def test_dates_and_unique_minutes(self):
        u="/files/NordicEquity-posttrade-2026-11-19T1550.csv"
        r=inspect(page(u,u,"/files/NordicEquity-posttrade-2026-11-19T1551.csv"),NOW)
        self.assertEqual(r["datedMinuteFiles"],2);self.assertTrue(r["recentFileDate"]);self.assertEqual(r["tradeFilesDownloaded"],0)
    def test_stale_and_cross_host(self):
        r=inspect(page("/files/NordicEquity-posttrade-2026-11-01T1550.csv","https://example.org/NordicEquity-posttrade-2026-11-19T1550.csv"),NOW)
        self.assertFalse(r["recentFileDate"]);self.assertEqual(r["datedMinuteFiles"],1)
    def test_invalid_and_future(self):
        r=inspect(page("/files/NordicEquity-posttrade-2026-11-19T2560.csv","/files/NordicEquity-posttrade-2026-12-01T1550.csv"),NOW)
        self.assertEqual(r["datedMinuteFiles"],0);self.assertFalse(r["dailyCompletenessVerified"])
