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
