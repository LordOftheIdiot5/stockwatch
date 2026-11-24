"""N04c candidate migration integrity using real in-memory SQLite; no remote writes."""
import sqlite3
import unittest
from pathlib import Path

SQL = Path(__file__).resolve().parents[1] / "docs/nordl-schema/0001_private_observations.sql"

class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        for migration in sorted(SQL.parent.glob("*.sql")):
            self.db.executescript(migration.read_text())
            self.db.executescript(migration.read_text())

    def tearDown(self):
        self.db.close()

    def revision(self, rev, value, sha):
        self.db.execute("INSERT INTO nordl_observation_revisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rev, "a"*64, "fixture", "series", "entity", "metric", "unit", "2026-11-01", value, None, sha, "private/"+sha))

    def receipt(self, rid, rev, date):
        self.db.execute("INSERT INTO nordl_retrieval_receipts VALUES (?,?,?,?,?)",
            (rid, rev, date, "fixture-policy", "private/"+rid))

    def test_revisions_and_retrieval_receipts(self):
        self.revision("b"*64, 10, "c"*64)
        self.revision("d"*64, 11, "e"*64)
        self.receipt("f"*64, "b"*64, "2026-11-02T00:00:00Z")
        self.receipt("1"*64, "b"*64, "2026-11-03T00:00:00Z")
        self.receipt("2"*64, "d"*64, "2026-11-04T00:00:00Z")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM nordl_observation_revisions").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM nordl_retrieval_receipts").fetchone()[0], 3)
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_orphan_receipt_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.receipt("f"*64, "b"*64, "2026-11-02T00:00:00Z")

    def test_duplicate_revision_and_object_rejected(self):
        self.revision("b"*64, 10, "c"*64)
        with self.assertRaises(sqlite3.IntegrityError):
            self.revision("b"*64, 11, "d"*64)
        with self.assertRaises(sqlite3.IntegrityError):
            self.revision("e"*64, 11, "c"*64)

    def test_raw_lineage_foreign_key(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO nordl_receipt_raw_lineage VALUES (?,?,?,?)", ("f"*64,"source-receipt","a"*64,"raw/object"))
        self.revision("b"*64, 10, "c"*64)
        self.receipt("f"*64, "b"*64, "2026-11-02T00:00:00Z")
        self.db.execute("INSERT INTO nordl_receipt_raw_lineage VALUES (?,?,?,?)", ("f"*64,"source-receipt","a"*64,"raw/object"))
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

if __name__ == "__main__":
    unittest.main()
