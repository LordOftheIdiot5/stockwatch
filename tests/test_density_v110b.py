"""Source-protection contracts for V110b compact workspace."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DensityTests(unittest.TestCase):
 def test_routes_load_compact_assets(self):
  for p in ('index','company','stocks','terminal','news','calendar','spreads','shipping','commodities','intelligence','compare','health'):
   t=(ROOT/(p+'.html')).read_text()
   self.assertIn('workspace-density-v110b.css?v=110b',t)
   self.assertIn('workspace-density-v110b.js?v=110b',t)
 def test_source_truth_and_reversible_layout(self):
  css=(ROOT/'workspace-density-v110b.css').read_text()
  js=(ROOT/'workspace-density-v110b.js').read_text()
  for token in ('.sw98-primary','.sw98-market-secondary','.sw110-heat-companion','.sw110b-jump','sw110b-spacious','.sw-company-tabs'):
   self.assertIn(token,css)
  for forbidden in ('fetch(', 'XMLHttpRequest','WebSocket','localStorage.setItem','innerHTML=', 'Math.random'):
   self.assertNotIn(forbidden,js)
  self.assertIn('MutationObserver(schedule)',js)
  self.assertIn('a.textContent=title',js)
if __name__=='__main__':unittest.main()
