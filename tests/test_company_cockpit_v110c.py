"""Company cockpit never replaces original issuer evidence or price series."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class V110cCockpitTests(unittest.TestCase):
 def test_existing_sections_and_source_controls(self):
  original=(ROOT/'v4.js').read_text()
  html=(ROOT/'company.html').read_text()
  js=(ROOT/'company-cockpit-v110c.js').read_text()
  for k in ('chart','financials','filings','peers','events','drivers','identity'):
   self.assertIn('data-company-section="'+k+'"',original)
  for k in ('company-cockpit-v110c.css?v=110c','company-cockpit-v110c.js?v=110c'):
   self.assertIn(k,html)
  for k in ('sw110cMode','sw110cTab','Full report','Focused view','MutationObserver',
            'section.hidden','advanced.length','setMode(false)','focus(\\'chart\\')'):
   self.assertIn(k,js)
  for forbidden in ('fetch(', 'XMLHttpRequest','WebSocket','innerHTML=', 'Math.random',
                    'localStorage.setItem', 'fake close','synthetic prices'):
   self.assertNotIn(forbidden,js)
 def test_full_report_can_recover_every_original_component(self):
  css=(ROOT/'company-cockpit-v110c.css').read_text()
  for k in ('data-sw110c-mode=focus','.sw-company-block[hidden]',
            '#companyDriverMap','.sw110c-mode','.sw110c-more'):
   self.assertIn(k,css)
  self.assertIn('for(const section of sections.values())section.hidden=false',
                (ROOT/'company-cockpit-v110c.js').read_text())
if __name__=='__main__':unittest.main()
