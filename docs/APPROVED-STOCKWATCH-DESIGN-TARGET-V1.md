# APPROVED DESIGN TARGET V1 — Nordl Stockwatch
**Approved:** 2026-11-21
**Master UX tracker:** [#165](https://github.com/LordOftheIdiot5/stockwatch/issues/165)
**Design roadmap:** [Visual Quality Workplan](VISUAL-QUALITY-WORKPLAN-20261121.md)
**Artwork:** ChatGPT Library `/Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png`
**Artwork SHA-256:** `df85998bd202dd9e4b3832a85edfaaf9fde78a417af4dcc3c7ced9e076be7b00`
**Reference resolution:** 1672 × 941 PNG. The image is saved in the user Library, not embedded as a binary in this GitHub PR.

## Decision — what to copy and what not to copy
This revised, **full-width** mockup is the approved public visual direction. Keep the dark Nordl Stockwatch brand, narrow/collapsible left task navigation, compact market tape, bold market overview title, visually generous hero chart, readable global-index cards, clear market-breadth KPI, latest verified news, improved sector heatmap, world-market geographic context, honest watchlists, quick tools and upcoming events.

**Non-negotiable:** the previous right-side "Target design level", improvement checklist, style palette, design goals or any other internal project-notes panel is **NOT part of the public website**. It must not be rendered, exposed as a default user sidebar, used to fill width, or added to desktop/mobile navigation. Keep that information only in GitHub issues/docs. The revised mockup has NO such panel; the full available width goes to actual product features.

All quotes, numbers, ticker levels, trend lines, event dates and map pins in the AI concept are illustrative. Do **not** publish them as live or delayed market observations, claim a source covers a country it does not, infer market cap/portfolio value, fabricate company news, or present a generated map/icon/chart as measured data. If we lack authorized series, show an honest dated empty/last-known state.

## Target visual hierarchy
**A. Global shell** — 180–220px collapsible sidebar on desktop (current source may differ; test first), keyboard searchable navigation, active route, compact top market tape, theme consistency, data-health/time/source indicator. Remaining page content is fluid with 16–28px responsive gutters.

**B. Hero row** — page title and short dated evidence-based summary, clear timeframe selectors and primary terminal/screener actions. Four geographic/index cards across at wide desktop *only when each has a real sourced, permitted series*. Sparkline plus latest as-of date and currency/units; never fake cards.

**C. Main analysis row** — a large 2-column or adaptive grid: **main interactive market chart as the dominant visual**, market snapshot (breadth/advancers/decliners with source denominator), geographically honest market cards, and actual latest filings/news. The legend/labels must be legible without zooming.

**D. Secondary intelligence row** — sector heatmap, rights-supported global-market map and saved lists/watchlists (only when actually implemented and user-authorized). Use real observed moves and dates. Distinguish a user watchlist from a fictitious demo sample. Map points use verified exchange indices or explicit country-level representative labels, no decorative fake performance.

**E. Action row** — compact, functional quick tools (screener, compare, research terminal, watchlist, earnings) and factual upcoming events with date/time-zone/source. Only show enabled features.

## Visual system and our own graphics
- Dark navy canvas and restrained teal/mint actions; cool cyan secondary accent; green gains/red losses accompanied by **+ / − text and icons** for accessibility, never color alone. Use existing brand colors as starting tokens rather than blindly copying generated hex colors.
- Clean rounded cards, subtle strokes and restrained glow around interactive chart highlights, not a permanent decorative gradient over every number. Minimum ~14px regular body at 100% zoom; 12px only for secondary metadata that remains legible. Fluid scale for headers, numbers and dates.
- Custom source-backed SVG/canvas sparkline engine, volume bars and crosshair with aligned tooltip, clear axes/date/units and browser keyboard equivalents. Do not generate fake price points or smooth over missing sessions.
- Heatmap includes clear legend, sector filter, exact equal-area or data-supported weighting explanation, hover/focus company card with session/time/status and permanent fallback to last known authorized observations.
- World-map artwork can be custom SVG/canvas with verified locations and dated source status, geographic clusters and keyboard-accessible fallback list; no unsourced illuminated points.
- News thumbnails/photos only where licensed; no generic ship/office imagery presented as the named company's property. Illustrations may be generic only when identified as decorative.

## Responsive rules and accessibility
At ≥1440px show full-width multi-panel composition; at 1024/768 collapse nonessential panels into useful rows; at 390/320 provide clean single-column flow, horizontal chart/table scrolling that remains keyboard reachable, no page-level overflow, and a usable nav drawer. Theme variants must both work. Target minimum ~44px touch area on mobile. Respect reduced motion. Provide accessible tab labels, source timestamps, screen-reader news/price summaries and visible focus.

## Version milestones / checkpoints
| Phase | Change | Exit criterion |
| --- | --- | --- |
| V90 · UX-S1/S2 | Fluid width, typography, skip-to-content, focus and nav clarity | Actual 1440/1920 screenshots show main canvas uses available area, no layout overflow; existing market data unchanged |
| V91 · UX-S4a | Existing native-chart controls readability and inspector | Real line/OHLC controls work on keyboard/mobile, no data or source regression |
| V92 · UX-S3 | Compose the Overview like this mockup: hierarchy, expanded hero chart, real index cards and news/market breadth | Screenshot comparison at 1440/1920, no internal goals sidebar, only source-backed figures and correct dates |
| V93 · UX-S5/S6 | Custom heatmap and global map graphics / source-aware hover and focus | Real evidence, verified geography/units, readable tiles, no fallback breakage, no fake global coverage |
| V94 · UX-S4b/S7 | Modern chart controls, chart/sector drilldowns, company/news/freight module consistency | Chart unit/time/legend provenance, explicit empty states, accurate cross-page navigation |
| V95 · UX-S8 | Sidebar/mobile navigation, component polish, 320/390/768/1024 usability, contrast, light/dark | Keyboard, touch and screen-reader QA; no clipped labels, invisible controls or page overflow |
| V96 · UX-S9/S10 | Full-site acceptance and production deploy validation | All data/heatmap regression suites + browser screenshot comparisons + deployment commit/source freshness verified |

Other V-series functional development may continue in parallel, but design and accessibility reviews are mandatory acceptance steps, not optional polish postponed forever.

## Audit process
Each two-version interval and after all chart/layout/menu changes, run existing visual_audit.py and targeted Playwright interaction tests at 320,390,768,1024,1440,1920; compare real screenshots against the approved reference. Verify 100%/200% browser zoom, light/dark, console/network issues, 24h source outages, last-known states, empty/no-data behavior, tooltip/selection, ticker-to-company drilldown, watchlist nav, heatmap legend, event source and chart range controls. Document evidence with date, source/revision, screenshots, automated vs manual, defects, fixes and re-test. Record open blockers in #165; do not mark done from a passing static audit.

## User acceptance / implementation notes
- The user explicitly approved this reference as the **level of polish to aim for**, not a request to publish fake market data.
- **Right-hand internal notes panel must never be user-facing.** The right side can contain real latest news, lists and actions, as shown in the revised visual.
- The user asked for the design goal to stay in the plan and continue being improved as new ideas emerge. Add discoveries to #165 and the source-controlled checklist rather than dropping unfinished work.
