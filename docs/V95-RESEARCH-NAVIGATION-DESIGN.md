# Stockwatch V95 — reference, methodology and typed intelligence visual quality
2026-11-21 · [Master design workplan #165](https://github.com/LordOftheIdiot5/stockwatch/issues/165).

## Implemented (draft PR only)
**Instrument directory:** Larger full-width source/reference hero, task shortcuts, keyboard-accessible search and MIC filters, legible source-count cards, scrollable reference table with region label, clearer paging and explicit warning that there are no connected quote prices. Raw OpenFIGI venue counts remain reference records, not unique issuers or priced listings.

**Research methodology:** Distinct blue evidence/standards visual identity, history → identity → research-universe jump navigation, evidence cards, source-rights explanatory sections and accessible coverage table. The pre-existing contradictory sentence about the OpenFIGI facilitator listing was replaced by the more precise statement that the listing grants no vendor-price display or Bloomberg endorsement. No price right was inferred.

**Intelligence graph:** New context legend and selected-instrument status above the existing typed graph. Branches, identifiers, sector peers and context remain the existing rendered source data. No ownership/cash-flow implication is added. Keyboard and touch users can interact with original instrument selector; a concise source warning is adjacent. Existing industry datasets and Nordl Energy nameplate capacity note are preserved.

Shared design: consistent approved dark/light Nordl palette, category-specific teal/blue accents, 320/390/1440/1920 responsive layouts, clear focus, skip-to-content and no public internal goals panel. No fabricated sparklines, prices, network flows, maps or images.

## Quality gates
`python -m unittest discover -s tests -p test_research_experience_v95.py -v`
`node --test tests/test_intelligence_experience_v95.mjs`
`python tests/browser_check_research_experience_v95.py` (24 route/device/theme screenshots)
Existing research, company network, source rights, navigation, mobile, price history and chart regression suites remain required. Run 768px, 200% zoom and real screen-reader/keyboard inspection separately. Observe actual source status when APIs fail and preserve truthful no-data states.

V96 must consolidate the stacked V90–V95 feature branches into a tested release candidate and verify deployed Cloudflare Pages SHA, canonical links, rights and real date freshness before production signoff.