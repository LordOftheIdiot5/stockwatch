# V92 — Approved Overview composition and first category-specific design rollout
**Status:** code committed, test/browser validation pending. **Date:** 2026-11-21.
**Approved visual reference:** Library `/Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png`. Permanent UX rubric: [Stockwatch master issue #165](https://github.com/LordOftheIdiot5/stockwatch/issues/165). First phases V90 #168 and V91 #169, then this V92 PR.

## What is actually changed
1. **Overview — source-backed chart-first composition.** Move the existing `sw-overview-workbench` (official EIA/FRED economic history only) out of the collapsed `overviewEconomy` section into a top-of-page `sw92-focus-grid` with existing market-breadth metrics. Historical series continue to use exact dated source observations and the existing keyboard crosshair. No invented Oslo Børs market-index graph or price level; the chart header stays explicitly labelled *Economic indicators* with source links.
2. Index cards fill available width when actual index feeds exist, with readable numerical hierarchy and sparklines. If only a few licensed indices exist, show only those. The stock market heatmap and real company news follow, with existing filters/fallback behavior preserved. New quick-tools navigation uses five existing routes only; **never show a right-side internal goals panel.**
3. Add `overview-design-v92.css` after V90 scoped CSS, preserving actual `v4.js` data/heatmap calculations.
4. Add `category-design-v92.css` **after existing CSS** on 10 important category routes. Shared typography, responsive panels, source-aligned focus, subtle distinct category accents. These are **first-pass foundations**, not completed category-specific graphic systems. Actual charts/maps/stock screens remain functional and unchanged.

## Underpage visual identity and next-specific work
| Route | Visual direction | Next content/graphic iteration |
| --- | --- | --- |
| Stocks & sectors | Data-rich mint/green; company identity and research first | Source-backed sector map, comparables and issuer cards |
| Research terminal | Dense cyan workspace with readable chart tools | Multi-chart time range, linked driver/crosshair inspection; verify licensing |
| News & filings | Editorial blue timeline with clear events & sources | Issuer chips, filing-vs-article treatments and event source thumbnails only with media rights |
| Shipping & freight | Ocean blue route workspace | Verified route map, dated index curves, tanker/bulk cards, units and shipping cost simulator |
| Commodities | Amber macro dashboard | Energy/metals filters, permitted price history, unit conversion and driver overlays |
| A/B spreads | Violet comparison/relative value | Dual share series, ratio chart, switching-cost calculator and right-of-market labels |
| Compare stocks | Side-by-side mint analysis | Peer comparison matrix, aligned sessions and explicit missing metrics |
| Earnings calendar | Purple time-oriented layout | Verified events timeline and category filters |
| Short positions | Neutral risk/compliance styling | Position timeline, official disclosure source and retention policies |
| Data health | Blue monitoring/diagnostics | Source uptime, last-known vs current observation, failures and collection latency |
| Research, instrument directory, company pages, intelligence graph | Separate shells not yet updated by this first wave | Later V93–V95 category-specific passes; preserve route/canonical/identity logic |

Shared shell: Nordl logo, navigation, search, dark/light modes, accessibility, coherent density and date/source badges; differentiated by actual task (chart-first, map-first, timeline-first, comparison-first). Do not turn every category into the same dashboard.

## Hard constraints
All prices, dates, country moves, candles, events, map markers and KPIs in the approved image are **illustrative**. No hardcoded financial results from the mockup. Official FRED/EIA are economic series, **not** Oslo or other exchange price history. The real index cards and heatmap retain existing approved data-rights gates. There are no new API calls except existing official history being fetched when the Overview loads, not only when details are expanded. This needs performance/network QA; if heavy, stage loading with an explicit user control without hiding the chart behind misleading fake data.

The right-side design-goals/navigation-panel from an earlier annotated concept is internal-only and never public.

## Validation
Run static tests:
```powershell
python -m unittest discover -s tests -p "test_visual_design_v92.py" -v
python -m unittest discover -s tests -p "test_overview_ux_v90.py" -v
python -m unittest discover -s tests -p "test_native_chart_ux_v91.py" -v
```
Run browser:
```powershell
python tests/browser_check_modern_overview.py
python tests/browser_check_approved_design_v92.py
python scripts/visual_audit.py --output visual-audit/v92 --pages overview stocks terminal news shipping commodities spreads compare calendar shorts health --devices desktop mobile small-mobile tablet wide
```
The dedicated V92 browser check covers 11 routes × 4 viewports × 2 themes and generates screenshots and JSON. Inspect 320px separately with visual_audit.py. Observe exact 100% browser zoom, 200% zoom, table and chart scrolling, UI interactions, source fallback and link navigation. Run full Python/Node regression suites; then verify Pages deployment SHA and the actual live website. Only after all gates pass should V92 be considered public-ready.

## Next planned versions
V93: separate category widgets and graphics based on actual data (heatmap, region map, freight route maps, company research); V94: richer charting controls and inspector; V95: responsive nav and accessibility across **all** inner pages including directory and company; V96: visual/device/data-rights full audit + staged deploy. Each phase logs evidence to #165 and preserves working market-data fallbacks.
