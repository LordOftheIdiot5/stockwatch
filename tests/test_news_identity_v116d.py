"""V116d: issuer identity collision and raw-source retention regression.

A headline about an acronym, brand product, sport or generic word is not an
issuer event. Keep its original URL/date in the review archive; never invent
a stronger match, alert, calendar event, or financial-driver classification.
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from news_quality import annotate, summary
from driver_attention import build as driver_attention
from build_research_data import extract_events
from scan import web_story_association

NOW=datetime(2026,11,21,21,tzinfo=timezone.utc)

class IssuerIdentityEvidence(unittest.TestCase):
    def row(self,ticker,name,title,**kw):
        return dict(id=ticker+':'+title[:20],ticker=ticker,name=name,sector='Research',
                    type='news',match='name_mentioned',published='2026-11-21T12:00:00Z',
                    headline=title,url='https://example.com/observed-story',
                    publisher='Source',**kw)

    def test_caf_football_acronym_cannot_become_spanish_rail_issuer_event(self):
        candidate=self.row('CAF.MC','CAF',
           "CAF launches U-17 Women's Africa Cup of Nations and opens bids for 2028 WAFCON")
        out=annotate([candidate])[0]
        self.assertEqual(out['relevance'],'review')
        self.assertEqual(out['identityTier'],'review_candidate')
        self.assertIn('rail/issuer',out['identityReviewReason'])
        self.assertEqual(out['driverTags'],[])
        self.assertEqual(out['url'],candidate['url'])
        self.assertEqual(out['published'],candidate['published'])

    def test_named_business_context_is_at_most_mentioned_not_verified(self):
        examples=[
           ('CAF.MC','CAF','CAF rail wins regional train orders'),
           ('FRO.OL','Frontline','Frontline plc announces quarterly tanker results'),
           ('AIR.PA','Airbus','Airbus signs aircraft order agreement'),
           ('RACE.MI','Ferrari','Ferrari NV raises annual guidance'),
        ]
        out=annotate([self.row(t,n,h) for t,n,h in examples])
        self.assertEqual([x['relevance'] for x in out],['mentioned']*4)
        self.assertEqual({x['identityTier'] for x in out},{'named_reference'})
        self.assertTrue(all('not issuer-confirmed' in x['identityReviewReason'] for x in out))

    def test_sport_person_product_and_generic_words_are_review_only(self):
        examples=[
          ('CAF.MC','CAF','Andrew Kamanga heads CAF football finance committee'),
          ('RACE.MI','Ferrari','Ferrari Challenge racing finals in Barcelona'),
          ('RACE.MI','Ferrari','Ferrari collision results in bizarre F1 crash'),
          ('AIR.PA','Airbus','Global Airlines sole Airbus A380 liquidation'),
          ('FRO.OL','Frontline','Financial fraud frontline hits mobile devices'),
        ]
        out=annotate([self.row(t,n,h) for t,n,h in examples])
        self.assertEqual([x['relevance'] for x in out],['review']*len(examples))
        self.assertEqual(summary(out)['withheldFromIssuerEvents'],len(examples))
        self.assertEqual(len(out),len(examples))
        self.assertTrue(all(x['identityReviewReason'] for x in out))
        attention=driver_attention(out,[{'ticker':'CAF.MC'},{'ticker':'RACE.MI'},
              {'ticker':'AIR.PA'},{'ticker':'FRO.OL'}],[],NOW)
        self.assertTrue(all(row['observedRecords']==0 for row in attention['listings'].values()))

    def test_real_issuer_code_disclosure_survives_and_is_strong(self):
        official=dict(self.row('CMBTO.OL','CMB.TECH',
             'CMB.TECH announces quarterly financial results on 24/11/2026'),
             type='disclosure',match='issuer_code',sourceIssuer='CMBTO',sourceFeed='newsweb',
             regulatory=True)
        out=annotate([official])[0]
        self.assertEqual(out['relevance'],'strong')
        self.assertEqual(out['identityTier'],'issuer_verified')
        self.assertEqual(summary([out])['issuerLinked'],1)
        self.assertEqual(len(extract_events([out],NOW)),1)

    def test_scanner_alert_gate_runs_before_archive_annotation(self):
        from news_quality import identity_evidence
        for ticker, name, title in (
            ('CAF.MC','CAF','CAF launches Women Africa Cup of Nations'),
            ('RACE.MI','Ferrari','Ferrari Challenge racing finals'),
            ('AIR.PA','Airbus','Airbus A380 plane grounded by airline'),
            ('FRO.OL','Frontline','Financial fraud frontline on mobile phones'),
        ):
            self.assertEqual(web_story_association(ticker,name,title)[0],'review')
        self.assertEqual(web_story_association('CAF.MC','CAF',
            'CAF rail wins train contract')[0],'mentioned')
        self.assertEqual(web_story_association('FRO.OL','Frontline',
            'Frontline plc announces tanker earnings')[0],'mentioned')
        self.assertEqual(web_story_association('RACE.MI','Ferrari',
            'Ferrari NV raises earnings guidance')[0],'mentioned')

    def test_review_tier_disclosure_cannot_generate_provisional_calendar_event(self):
        suspected=dict(self.row('CAF.MC','CAF',
          'CAF announces quarterly results on 26/11/2026'),
          type='disclosure',match='unverified')
        # Test a genuinely unrelated acronym so the headline is reviewed.
        suspected['headline']='CAF Africa football announces earnings on 26/11/2026'
        out=annotate([suspected])[0]
        self.assertEqual(out['relevance'],'review')
        self.assertEqual(extract_events([out],NOW),[])

if __name__=='__main__':
    unittest.main()
