# V93 — Heatmap inspection and category-specific sourced graphics
Date: 2026-11-21. Master UX workplan: https://github.com/LordOftheIdiot5/stockwatch/issues/165

## Implemented in draft
Overview and Stocks heatmaps now have more readable sector tiles, optional larger tile sizing, and a focus/hover inspector of the real rendered source information, dated movement and retained/older-data notice. A visible-tile balance strip summarizes the currently rendered CSS tile classes, never the complete equity-market breadth. Clicking an original tile still opens the same company/directory page.
Existing V4 data rights, market observation quality, A/B daily-move and saved last-price fallback are untouched. The inspector uses no network fetches, cookies, storage or prices outside existing rendered tile metadata.
Shipping route and USDA historical index widgets, commodity tables, news timeline, A/B spread tables and Data Health source-coverage panels have new category-specific design styles without changes to observed numbers or source series.

## What remains on the roadmap
No market-cap-weighted heatmap or world-market geographic map is claimed: both require verified licensed company-size or index/region coordinates. Further V93b/V94 research widgets will be added only when these data rights and identifiers are available. Source-specific company pages and research directory deeper redesign belong to V94–V95. The private Target design level / goals panel does not appear on the public website.

## Validation (not yet run in user checkout)
From the Stockwatch repository:
node --test tests/test_heatmap_experience_v93.mjs
python -m unittest discover -s tests -p test_heatmap_experience_v93.py -v
python tests/browser_check_heatmap_v93.py
python tests/browser_check_modern_overview.py
python scripts/visual_audit.py --output visual-audit/v93 --pages overview stocks shipping commodities news spreads health --devices desktop mobile small-mobile tablet wide
Review 320px, 390px, 768px, 1440px and 1920px dark/light screenshots and keyboard navigation. Check dynamic filters, no-data/older observations, original link behavior, chart/heatmap fallback, no horizontal overflow, and no console exceptions. Run full Python/Node regressions and live Pages deployment-SHA verification before signoff.
