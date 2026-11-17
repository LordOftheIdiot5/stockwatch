# Stockwatch V47–V60: locked product and design roadmap
Owner-approved scope: 2026-11-17. This is the canonical checklist; do not silently remove or renumber deliverables. A version is done only when implementation, tests, live deployment and a post-deployment check are evidenced. Mark partial work as partial, not complete.
## Visual target
User's reference screenshot: professional dark multi-chart financial terminal, upper control strip, dense drawing toolbar, multiple synchronized price/indicator panes, right-side research/watchlist controls, colored heatmap screener and compact market tables. Match its functional hierarchy and density, not copied branding. Stockwatch uses its own mint/navy palette and accessible light theme. Never render fabricated market candles to fill empty panels. Desktop is a real working terminal; mobile uses simplified one-pane tabs and touch controls, not a scaled-down desktop.
## Existing baseline and dependencies
Current live audit: run 44136272138 (17 pages, 34 captures); 138 tracked listings. PR #35 native chart navigation (review against latest main before integrating), #58 V46 private research assets, #57 identity repair, #56 trial validation, #55 direct exchange audit, #51 licensed adapter, #47 SCB metadata, #43 exchange profile. Do not discard these branches or duplicate their components. Resolve merge conflicts and establish rights before activation. Trial quotes must never enter archive or public chart/export; separate internal storage, public display, derivative use and dataset resale rights. No new paid services authorized by this roadmap.
## Releases
| Version | Deliverable | Acceptance gate |
|---|---|---|
| V47 | Shared navigation, theme, responsive shell and route consistency across all 17 core pages | Every page is discoverable desktop/mobile; active state, keyboard access, both themes, no duplicate nav, old deep links retained |
| V48 | Mobile compact mode, bottom navigation, collapsible long sections, searchable/paged lists, sticky table headers, touch targets | 320/390/768 widths, no body horizontal overflow, tables may scroll inside container; no loss of content or accessibility; report before/after mobile page height |
| V49 | Native advanced chart engine and multi-chart workbench; integrate PR #35 | Full chart area; line/candle based on genuine OHLC only, crosshair, wheel/pinch zoom, drag pan, time range, reset, price/time axes, volume when present, drawing tools, SMA/EMA/RSI, synchronized panes; no fabricated OHLC; test mouse/touch and no-data state |
| V50 | Company research workspace | Larger chart, source dates, issuer identity, reported financial statements, peers, disclosures and corporate actions; missing fields explicit |
| V51 | Stock screener and heatmap | Search/filter market/sector/currency/coverage, sortable columns, saved column presets, neutral missing-data tiles, no mixed-session ranking |
| V52 | Research terminal polish | Resizable panes, multi-chart layout, watchlist, toolbar, saved layout and focus mode; shareable URL where appropriate |
| V53 | A/B and cross-listing analysis | Verified security/issuer relationships, same-session alignment, currency conversion where authorized, liquidity, transaction costs, historical premium & robust statistics; no trade recommendation |
| V54 | Financial statement and corporate-action history | Period/currency/source evidence, revision history, splits, dividends, symbol/ISIN changes; never automatically concatenate different securities |
| V55 | Connected industry intelligence | Company-to-driver links for salmon, industry, energy, shipping and commodities; provenance, chart time alignment, no invented causality |
| V56 | Shipping and freight intelligence | Route maps, categories, voyage economics, unit/date/source distinctions; licensed freight only where authorized |
| V57 | Global research search | Unified index of companies, instruments, news, economic series and catalog; filter and keyboard support, no private payloads |
| V58 | Commercial data portal | Product metadata, schemas, source/rights/coverage manifests, controlled exports only following explicit commercial authorization; no public trial data |
| V59 | Saved workspace and watchlists | Local persistence, load/save/reset, export/import preferences; no account claims unless actual backend exists |
| V60 | Release quality and production readiness | Full desktop/mobile/light/dark screenshot matrix, accessibility, performance, data freshness, permissions, links, no uncaught errors, release evidence; 138 listings remain tracked, unavailable sources labeled |
## Release process
1. Check current main, open PRs and preceding stage; no blind merges or production overwrites.
2. Work on a versioned branch; write tests and changelog. Reuse existing business logic rather than parallel implementations.
3. Run unit/integration tests and rendered-browser checks, capture desktop (1440), tablet (768), mobile (390/320); light/dark and keyboard. Inspect screenshots, CSS load, layout geometry, page errors and source failures.
4. Merge only reviewed/compatible changes; verify deployed revision and repeat live checks. Keep release ledger with PR, commit, test run, deployment, coverage and known gaps.
5. Keep provider onboarding parallel; no fake historical data, unauthorized redistribution, new subscription or publication of private warehouse.
## Ledger
- V46 research assets: PR #58 open; initial checks passed; deployment pending. Chart navigation PR #35 open. Both are dependencies, not completed releases.
- V47: implementation in progress on feature/stockwatch-v47-unified-shell-20261117; shared navigation and initial mobile foundation. Other gates open until verified.
- V48–V60: planned.
