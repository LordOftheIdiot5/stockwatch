"""Recovery must never prune historical IDs or silently skip missing configuration."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from push_archive import load_items, pack_batches, main

class ArchiveRecovery(unittest.TestCase):
    def test_full_replay_reaches_older_partitions_and_is_idempotent_by_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / 'data' / 'news-store'
            store.mkdir(parents=True)
            def item(id, date):
                return {'id': id, 'published': date, 'url': 'https://example.com/' + id}
            old = item('older', '2026-05-26T12:00:00Z')
            new = item('newer', '2026-11-19T12:00:00Z')
            (store / '2026-05.json').write_text(json.dumps({'items': [old]}))
            (store / '2026-11.json').write_text(json.dumps({'items': [old, new]}))
            now = datetime(2026, 11, 19, 18, tzinfo=timezone.utc)
            rows = load_items(root, backfill=True, now=now)
            self.assertEqual([r['id'] for r in rows], ['older', 'newer'])
            self.assertEqual(rows, load_items(root, backfill=True, now=now))
            self.assertEqual([r for batch in pack_batches(rows) for r in batch], rows)

    def test_recovery_fails_when_secret_missing(self):
        with patch.dict(os.environ, {'STOCKWATCH_ARCHIVE_URL': '', 'STOCKWATCH_ARCHIVE_TOKEN': ''}):
            with self.assertRaisesRegex(SystemExit, 'requires an endpoint'):
                main(['--backfill', '--require-config'])

    def test_optional_scanner_ingestion_stays_nonblocking_if_unconfigured(self):
        with patch.dict(os.environ, {'STOCKWATCH_ARCHIVE_URL': '', 'STOCKWATCH_ARCHIVE_TOKEN': ''}):
            self.assertEqual(main([]), 0)
