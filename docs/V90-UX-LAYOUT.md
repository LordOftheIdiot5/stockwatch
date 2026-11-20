# Stockwatch V90 — First layout, navigation and readability implementation
Date 2026-11-21 · Master issue [#165](https://github.com/LordOftheIdiot5/stockwatch/issues/165) · Source-controlled plan [PR #166](https://github.com/LordOftheIdiot5/stockwatch/pull/166).

## Why this first
Screenshot suggests main market content is too narrow relative to available desktop width. The checked-in `overview-v89j.css` already tries a 1,760 CSS px cap with centered margins, so on ultra-wide CSS viewports or reduced browser zoom this can create large blank margins. Screenshot zoom/deployed commit was not independently verified; the new browser diagnostic measures actual CSS boxes to validate the hypothesis.

## This change
- Add `overview-ux-v90.css` *after* existing `overview-v89j.css` and scope it to the Overview page. Replace centered max-width with fluid content and modest gutters.
- Improve legibility of the overview KPIs, index cards, sparklines, source dates, news entries, heatmap labels, navigation and global search. Keep market-data text/source distinctions and existing heatmap behavior unchanged.
- Preserve existing menu labels/routes and mobile bottom-nav. Add keyboard skip-to-main, visible focus, scrollable regions and mobile-safe grid breakpoints.
- Extend `scripts/visual_audit.py` with optional 320/768/1920 captures and dimensions for content coverage and right gap. Defaults remain the existing 1440/390 devices, so existing CI runs are not made more expensive.
- Add isolated V90 static tests and a 10-view Playwright layout audit (320,390,768,1440,1920 × dark/light) that captures screenshots and verifies right margin/coverage at 1440/1920 and no page overflow; no exchange/data API change.

## QA gates (NOT yet executed on the new source)
```powershell
cd C:\stockwatch
python -m unittest discover -s tests -p test_overview_ux_v90.py -v
python -m unittest discover -s tests -p test_overview_v89j.py -v
python tests/browser_check_overview_layout_v90.py
python scripts/visual_audit.py --output visual-audit/v90 --pages overview stocks news terminal --devices desktop mobile small-mobile tablet wide
```
Run existing browser_check_modern_overview.py and retained heatmap/shell tests. The Playwright script requires Chromium; if the market app cannot load data, distinguish local/CORS network failures from actual visual/layout issues. Run live smoke after deploy and compare screenshot with user image and actual desktop browser zoom.

## Next phases
UX-S2 deep nav/menu usability, UX-S3 overview hierarchy, UX-S4 chart toolbar/crosshair/units, UX-S5 heatmap visual/tooltip, UX-S6 global market pulse, UX-S7 company/news/freight, UX-S8 accessibility/performance. At least every two feature versions and any layout/chart/menu change, rerun desktop/mobile/dark-light screenshots, interaction checks and recorded defect severity. No redesign status is complete without browser evidence and actual deploy SHA.
