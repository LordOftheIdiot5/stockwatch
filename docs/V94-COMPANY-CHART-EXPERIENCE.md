# V94 — Source-first company research and chart design
Date: 2026-11-21 · Master roadmap: https://github.com/LordOftheIdiot5/stockwatch/issues/165

## Scope
The company page retains its existing real identity, latest observed price/date/status, issuer coverage, authorized historical-series chart, optional issuer photo and provenance, event evidence, financial statements, peer list, driver network and industry context. V94 makes price history the first research workspace rather than burying it below the driver map. The original map is reparented as an existing DOM node **after the chart**, preserving its event listeners and source-linked content.
New scoped CSS establishes a spacious dark Nordl company identity header, explicit price-date and source treatment, 5-part research coverage strip, sticky keyboard-friendly section navigation, larger chart toolbar/axes and legible financial statement cards. Small screens become single-column with 44px chart controls. The chart is a verified series only if existing V49 rights gates allow it; a missing source stays empty with the original warning. No mockup price levels, artificial price history, inference about supplier financial flows or unsourced photos.

## Interaction and accessibility
V94 enhancer attaches to dynamically rendered company content. Seven existing sections get stable IDs and `aria-controls`, selected navigation state and Arrow/Home/End focus navigation. Explicit chart region and live source status announcements improve accessibility. Link shortcuts jump to already-existing financial, identity and company-update sections. Reference-only unpriced listings retain a distinct evidence-grid design; FIGI candidates stay unverified.

## QA
From Stockwatch root:
node --test tests/test_company_experience_v94.mjs tests/test_company_v50.mjs
python -m unittest discover -s tests -p test_company_experience_v94.py -v
python tests/browser_check_company_experience_v94.py
python tests/browser_check_company_v50.py
python scripts/visual_audit.py --output visual-audit/v94 --pages company stocks terminal --devices desktop mobile small-mobile tablet wide

Run browser QA at 390/768/1440/1920 in dark/light; separately inspect 320px and 200% zoom, keyboard and touch, image rights/captions, licensed 25-bar test fixture vs no-history state, accurate source time/currency and absence of horizontal scroll. Existing Python and Node market regression gates must still pass. Full release and live Pages SHA verification are not implied by a passing static or local screenshot test.

## Next
V94b can add evidence-rich company relationships and chart data-table accessibility using existing verified relationships and price permissions; V95 covers standalone directory, research and graph page consistency, V96 production audit. No internal design-goal panel appears on public pages.