from __future__ import annotations
import json,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from push_archive import load_items,pack_batches,clean_token

class IngestTests(unittest.TestCase):
    def test_clean_token_removes_bom_without_weakening_validation(self):
        token = '0123456789abcdef' * 4
        self.assertEqual(clean_token('\ufeff' + token + '\n'), token)
        self.assertEqual(clean_token(token), token)
        with self.assertRaises(ValueError):
            clean_token(token + '💥')
        with self.assertRaises(ValueError):
            clean_token('not-a-token')

    def test_batches_under_size_and_count_limits(self):
        items=[{'id':str(i),'published':'2026-11-12T12:00:00Z','url':'https://example.com','headline':'x'*700} for i in range(215)]
        parts=list(pack_batches(items,max_bytes=14000))
        self.assertEqual(sum(len(x) for x in parts),215)
        for batch in parts:
            self.assertLessEqual(len(batch),100)
            self.assertLessEqual(len(json.dumps({'items':batch},ensure_ascii=False,separators=(',',':')).encode()),14000)
    def test_full_backfill_and_rolling_window(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'data/news-store').mkdir(parents=True)
            old={'id':'old','published':'2026-10-02T11:00:00Z','url':'https://example.org/old'}
            new={'id':'new','published':'2026-11-12T11:00:00Z','url':'https://example.org/new'}
            (root/'data/news-store/2026-10.json').write_text(json.dumps({'items':[old]}))
            (root/'data/news-store/2026-11.json').write_text(json.dumps({'items':[new,new]}))
            (root/'data/news-archive.json').write_text(json.dumps({'items':[old,new]}))
            now=datetime(2026,11,13,tzinfo=timezone.utc)
            self.assertEqual([x['id'] for x in load_items(root,backfill=True,now=now)],['old','new'])
            self.assertEqual([x['id'] for x in load_items(root,now=now)],['new'])

if __name__=='__main__': unittest.main()
