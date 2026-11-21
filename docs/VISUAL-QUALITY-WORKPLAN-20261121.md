# Nordl Stockwatch — visual quality baseline and redesign workplan
Date: 2026-11-21 · Master tracker: [#165](https://github.com/LordOftheIdiot5/stockwatch/issues/165) · Evidence: user-supplied 1834×832 desktop screenshot of Stockwatch overview on 2026-11-20. This is a screenshot-only assessment; the actual deployed revision, 100% zoom and browser behavior remain to be checked.

## Priorities (preserve existing brand and functioning market data)
| Order | Area | Screenshot finding | Target change | Acceptance |
| --- | --- | --- | --- | --- |
| 0 | Layout / viewport | Main page appears confined to middle/right with substantial unused area beyond sidebar | Inspect parent/wrapper sizing: `index.html`, `v4.css`, `overview-v89j.css`; use fluid responsive content with controlled gutters and balanced columns | At 1440/1920, 100% zoom, no unintended dead zone or page overflow; before/after screenshots |
| 1 | Typography / hierarchy | Small ticker/news metadata, numerous mini labels and low emphasis | Standardized type scale, larger key numbers, clear as-of dates and source labels; tokenized light/dark contrast and focus | Main text readable at real zoom, tested 200% zoom; at least 14px ordinary text as a target, WCAG contrast review |
| 2 | Navigation | Many tiny sidebar destinations, small categories, mobile discoverability unknown | Group by user task; collapsible desktop side, sensible mobile drawer/bottom nav, persistent active path, keyboard focus and optional search | Every existing route reachable from 390px/keyboard; no dead links or obscured controls |
| 3 | Overview story | Breadth cards, three Taiwan indices, dense map/news with no clear session headline | Source-backed one-line session summary, market breadth, date/freshness, primary visual, relevant news, expandable detail | Visitor can answer “what moved, when, from what source?” in one glance |
| 4 | Native charts | Tiny top sparklines, primary full chart not prominent | Legible axis/currency/unit, range tabs and consistent crosshair/tooltips, source/date, range comparison only for aligned sessions; show stale/gaps | Empty/one-point/history gaps graceful; no fabricated candles/prices; accessible summary table |
| 5 | Heatmap | Uniform dense tiles and overwhelmingly red palette | Better tile spacing/contrast, hover/focus details, clear sector filters and legend; equal-area clearly explained, optional weighting only with licensed size data | Heatmap readable at 320/390/1440, never disappears when source fails; fallback dated |
| 6 | Global index cards | “Global” section with only 3 Taiwan-related observations, could overstate coverage | Region/source labels, expand when real official/licensed data exists, keep unavailable markets explicit | No unsourced index card or fabricated session |
| 7 | News/company pages | News rows tightly packed; issuer correlation not highlighted | Evidenced dated headlines, issuer chips, filing vs commentary; source-linked company drilldown and timeline | Clear separation of fact from inference, no invented impact claims |
| 8 | Shipping, A/B, commodities, research | Dense data needs repeated manual interpretation | Shared panel, evidence, chart and unit conventions; progressively reveal technical drivers, shipping contract terms and alerts | Documented units, licensing/staleness, examples tested per module |
| 9 | Continuous release audits | Static tests alone cannot prove visual correctness | Automated Playwright screenshots, interactions, dark/light, mobile, contrast and production smoke alongside existing data/source tests | 320/390/768/1024/1440/1920, keyboard and browser sessions, 0 critical/major unresolved regressions |

## Screen architecture to explore
Desktop, not final pixel specification:

```text
┌─ persistent/sidebar tasks ─┬─ source status / market as-of / global search ─────────────────────────────┐
│ Overview                   │ Market overview: dated takeaway + source/freshness and key market KPIs    │
│ Research / Stocks          │ Index strip (actually connected regional indices)                        │
│ Compare / News             │ Primary market chart with range, unit, tooltip      │ Relevant intelligence │
│ Shipping / A-B / More      │ Heatmap (clear legend/filter, optional expand)     │ Filings / news         │
│ Data/Methodology           │ Evidence and deeper research, collapsible modules                            │
└────────────────────────────┴────────────────────────────────────────────────────────────────────────────┘
```

Do not fill empty zones with invented data. If fewer official indices or prices are licensed, design the empty state honestly rather than fabricating a chart. No arbitrary market-cap weighting when sizes are unverified.

## QA implementation
Existing test assets: `scripts/visual_audit.py`, `tests/browser_check_modern_overview.py`, `tests/browser_check_shell_v47.py`, `docs/visual-audit.md`, `native-chart.js/css`, `overview-v89j.css`, `global-market-pulse.js`. Start with the existing infrastructure:

```powershell
python -m pip install playwright==1.56.0
python -m playwright install chromium
python scripts/visual_audit.py --output visual-audit/checkout
python scripts/visual_audit.py --base-url https://stocks.nordl.dev/ --output visual-audit/live --pages overview stocks company terminal shipping spreads calendar health
```

Run 1440×1000 and 390×844 from the current script first; extend 320, 768, 1024 and 1920 plus dark/light, keyboard, zoom, chart tooltip and heatmap failure tests. Record screenshot assets privately or as intended CI artifacts. Compare live deploy SHA with `main`: visual screenshot might show a different version. An audit result must record checked date, revision, viewports, theme, page, console errors, broken links, missing imagery, horizontal overflow, low contrast, click flow, screenshot location, severity, fix PR and retest. Update #165 after each two versions or any menu/chart/layout change.

## Release criteria and data guardrails
No net loss of working UI routes, heatmap coverage, price last-known fallback, news source matching, A/B spread or shipping research. All market prices must have authorized rights and explicit session/time/currency; chart improvements may not fill gaps with fabricated values. No new trackers without privacy review. Reuse rights-reviewed photography; never represent a generic vessel/HQ as an issuer's property. Preview/static QA and browser QA are separate gates. Verify production deployment after merges.

## Shared Nordl consistency
Coordinate cross-site visual standards with [Leivro master plan #172](https://github.com/LordOftheIdiot5/models/issues/172). Shared fundamentals: sensible typography, responsive/accessible controls, clear data provenance, graceful missing data, professional visuals. Stockwatch can remain a dense terminal; Leivro is a consumer-facing shopping decision platform and Energy is map/chart-first—do not force identical homepage layouts.

## Approved mockup reference (replaces annotated concept)
See [Approved Stockwatch Design Target V1](APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md). The reference image is stored in the user's Library at `/Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png`. This is the **public UI direction without any right-side internal goals/style/palette panel**. The right column of the public dashboard is genuine research content. Source-aligned numbers only; concept imagery is illustrative. Apply the V90–V96 acceptance gates and preserve currently functioning data/heatmap fallbacks.


## V116 integrated design acceptance — active release gate

Read [V116 integrated design acceptance](V116-INTEGRATED-DESIGN-ACCEPTANCE.md) for exact V115 checkout defects, owner reference SHA-256, 19-route × 6-width × 2-theme browser evidence, source-offline and zoom proxy, unclosed issues, and the explicit rule that a green test does not mean final visual sign-off.

## 2026-11-21 V111–V116 — screenshot-to-reference gap and all underpages

**Owner screenshots:** `image(20261121-161609).png` (top Overview) and `image(20261121-161602).png` (lower Overview) at approximately 1988px wide. Compare with the *approved* 1672×941 full-width reference recorded in [APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md](APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md). That reference is a **concept**, including illustrative prices, maps, events and watchlists, not an approved market data source. Retain all real-price/source/status guards and no internal design checklist in public pages.

### Observed visual differences, not yet a final rendered browser acceptance
- **Top:** current production captures use three real Taiwan indices, a modest FX macro chart, compact breadth/news and narrow 10–12px controls. Approved target features a larger dominant interactive market chart, stronger labels, balanced right-side intelligence and indices from multiple regions **only if rights-approved actual data exists**. Never fabricate Norway/Paris/US index levels to fill cards.
- **Heatmap:** when expanded, the inspector appears only inside the first dashboard column, leaving a large unused area on the right (visible in first screenshot). V111 uses full-width grid spanning so the inspector and tiles can use available desktop width; test actual `getBoundingClientRect` at 1440/1920 after clicking Expand map and collapse.
- **Lower:** sector cards, stock-event cards and collapsed economics/infrastructure panels look functional but visually dense or too small. These are legitimate depth modules, not all equally deserving primary screen area. Group by customer task and give substantive working research links, not decorative content.
- **Data truth:** 136 visible heatmap tiles and 152/500 dated listing observations cannot be relabelled live index or completed-session breadth. No fake event calendar, portfolio returns, assets or watchlist holdings.

### Underpages are first-class design objectives, not an afterthought

Each entry requires desktop (1440/1920) + phone (390/320), dark/light, real keyboard and link flow, source/freshness, informative loading/fallback, and a consistent branded header/nav. **No route can be considered visually finished solely because Overview is.**

| Group | Routes | Primary task and visual acceptance |
| --- | --- | --- |
| Core trading research | `terminal.html`, `stocks.html`, `company.html`, `compare.html` | Large real chart/issuer identity; clear quote session and currency; easy filters and comparison; no hidden navigation or incorrect stale comparison |
| Events and market drivers | `news.html`, `calendar.html`, `spreads.html`, `shipping.html`, `commodities.html`, `shorts.html` | Dated source-backed events; distinguish disclosures from future schedules; correct share-class ratios, freight/commodity units and delayed/missing states |
| Relationships and discovery | `intelligence.html`, `search.html`, `directory.html`, `research.html` | Search, select, graph and verify citations; no unverifiable transaction amounts; clear coverage identity and accurate route transitions |
| Data products and trust | `price-history.html`, `health.html`, `data-products.html` | Last-known vs licensed EOD distinction, source health and gaps, real export/API availability, no deceptive empty history or paid endpoint |
| Entry + overview | `welcome.html`, `index.html` | Product promise, immediate next action, verified current/delayed as-of, source-backed first visual, stable navigation and full-width expanded map |

### Release sequence and gates
- **V111 immediate, screenshot defect:** fix full-width expanded heatmap and restore legible chart/index/news label sizes; add shared readability layer to all 19 routes. No data changes. Run dedicated browser regression and existing screenshots before promoting.
- **V112 navigation/design cohesion:** audit `directory/research/search/data-products/welcome` legacy brand-shell variants against the other 14 workspaces, consolidate duplicate navigation and style only after measuring. Preserve every original route and correct canonical/SEO paths.
- **V113 company and core trading UX:** prioritize company profile → chart → sourced events/relationships, compare/screener and terminal research; no invented fundamentals, market caps or historical candles.
- **V114 secondary market intelligence:** improve A/B, freight, commodities, shorts and calendar with task-specific visuals where permitted observations exist; meaningful dated fallback when absent.
- **V115 data and conversion pages:** honest licensed-price archive, full source-status, data-product sample/API docs with real working contact path. Avoid subscription signups until actually implemented.
- **V116 integrated visual certification:** capture and review top/middle/bottom and interaction screenshots for **all 19 routes** at 320/390/768/1024/1440/1920, plus dark/light, keyboard, 200% zoom and offline/stale fixtures. Record deviations from reference, source hashes, live deployed SHA, regression count and remaining defects in [master issue #165](https://github.com/LordOftheIdiot5/stockwatch/issues/165). Never claim a full rendered UI audit solely on code review or supplied screenshots.

**Acceptance target:** No misleading live freshness, no page-level horizontal overflow, legible first fold, no empty right half when expanding heatmap, at least one verifiable customer action per page, and no broken return path to Overview. Mobile panels must allow keyboard focus and scrolling; all underlying company/chart/market data must remain unchanged by presentation-only work.
