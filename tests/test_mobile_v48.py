from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Mobile48(unittest.TestCase):
    def test_pagination_hooks(self):
        v=(ROOT/'v4.js').read_text()
        r=(ROOT/'research.js').read_text()
        self.assertIn('arr.slice((routePage-1)*size,routePage*size)',v)
        self.assertIn('const size=6,total=',v)
        self.assertIn("routePage=1;draw()",v)
        self.assertIn('filtered.slice((current-1)*size,current*size)',r)
        self.assertIn("renderRows(rows,'d1Results',100,true)",r)
        self.assertLess(r.index('<h2>Search persistent news database'),r.index('<h2>Latest 100 updates'))
    def test_css(self):
        c=(ROOT/'shell-v47.css').read_text()
        self.assertIn('position:sticky;top:0',c)
        self.assertIn('min-height:44px',c)
