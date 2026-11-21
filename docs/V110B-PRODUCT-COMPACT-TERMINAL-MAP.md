# Stockwatch — compact terminal and differentiated company intelligence plan (V110b–V112)

Approved image location: ChatGPT Library /Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png
Reference SHA256: df85998bd202dd9e4b3832a85edfaaf9fde78a417af4dcc3c7ced9e076be7b00.
Issue trackers: #165 approved design, #185 data acquisition and #176 price freshness.

## 1. Reproduce the screenshot's real layout, NOT its invented numbers

The mockup is a spec for full-width shell, navigation, typography, visual hierarchy, chart controls, index cards, news, breadth, sector map, world context, watchlists and compact quick tools.

| Approved zone | Data/UX implementation | Source-safe limitation |
| --- | --- | --- |
| Collapsible left sidebar and compact ticker tape | Keep all functional Nordl shell routes, source-labelled market tape, global search | Never badge sources as live unless verified |
| Main hero + timeframe and screener | Minimal title/date/screener controls; real period picker tied to verified data | Disable/index source label until historic equity bars permitted |
| Four diverse index cards | Distinct market/venue identities, official dates, sparkline + exact licence | Present only the actual Taiwan cards and source-backed FX until Nordic/US/Europe index licences |
| Dominant market chart | Real existing FX/macro now, authorized equity OHLC/intraday chart after source approval | A macro chart must not be falsely labelled an OSEBX index chart |
| Breadth + news + verified events | Session comparison with explicit denominator, original issuer announcements and source links | A disclosure filing date is not automatically a future earnings date |
| Sector heatmap + world context + saved lists | Honest equal-area dated movements, geographic context where actual permitted data and user-saved tickers | No invented globe dots, portfolio returns or global performance |
| Quick tools and event ribbon | Actual functioning screener, compare, terminal, earnings and verified source-linked calendar | Show unknown where future dates are missing |

The screenshot can be matched in spacing and layout before providers are connected. The figure values in the image are illustrative and must NOT be copied into production.

## 2. Root problem

Years of style additions and dynamic v4.js panel moves produced a tall, uneven page; functionality and source collection were delivered separately. Fix through a cohesive layout contract, actual component reuse, compact top screens and page-specific drilldowns, not more arbitrary panels.

## 3. V110b — 12-route density release

Add workspace-density-v110b.css and workspace-density-v110b.js to Overview, Company, Stocks, Terminal, News, Calendar, Spreads, Shipping, Commodities, Intelligence, Compare and Data Health.

At desktop widths >=1320px use: a compact hero, source index cards, macro/FX chart + breadth/news side rail, then a three-column row of actual sector heatmap, biggest movements and personal watchlist, then actual tools/events. The heatmap remains expandable, and all price-only/missing movement states are available via its existing filters. No prices are manufactured.

For menu routes use compact section/card/metric spacing, bounded independently scrollable data tables with sticky table headers, and a real jump-link strip to existing section headings. Provide a reversible Full layout / Compact layout control so no content is lost. Company and Terminal already have dedicated navigation; do not add redundant auto-navigation to those routes.

Verify 320/390/768/1024/1440/1920 dark/light, focus, chart keyboard, no horizontal overflow, retained feeds, outage fallback, and actual Pages asset checksums. A screenshot of a fixture is QA, not proof the data is current.

## 4. V110c–V110e — continue until product-quality target

**V110c Company intelligence cockpit:** Replace jump-only research sections with functional, reversible tabs that default to a concise evidence-backed overview, keeping the full original source library reachable. Main company view: issuer identity, latest price observation/status, genuine price/history chart, authoritative financial statements, original events, counterparties/owners, exposures and drivers. Add a source/freshness grade; do not invent an AI score, news or issuer relationships.

**V110d Source-backed global geography and research features:** Introduce only permitted Nordic/European/US/Asian index/FX historical observations with exact dates; use a verified and keyboard-accessible geography UI. Integrate authentic market history, company data graph and saved watchlists; no fake intraday points, no synthetic maps.

**V110e Full site visual acceptance:** Compare actual screenshots to the approved full-width PNG at all viewports and both themes. Check source provenance and all expanded states, keyboard/mobile drawers, touch targets, first-fold visual density, per-company task success, production commit parity and zero important broken links.

## 5. Unique per-company information (product thesis)

The value is not stock-price charts alone. Each company needs a joined, **source-cited causal research workspace**:
1. Exact issuer/listing identity, ISIN/MIC/LEI/CIK, currency, share class, original quote date, licence.
2. Dated official financial periods with revisions, revenue, cash flow, margin, debt, capex and dividend history.
3. Original exchange/SEC/ESEF disclosures, issuer updates, corroborated future events and change timelines.
4. Verified named customers, suppliers, joint ventures, owners, financing and contracts: counterparty role, evidence URL, date, known amount, non-inferred conditions. An announced order is not already collected revenue.
5. Company-specific operating drivers: energy use and electricity zones, fuel/metal inputs, shipping/freight route exposure, rates/FX, infrastructure constraints — only when the named company's exposures have documentary evidence.
6. A/B class comparison, trading costs, real spread histories, equity liquidity and short-position context.
7. What changed since the last *actual* source observation, with exact document/period comparison and explicit uncertainty; never use a generic headline co-mention as a verified supply relationship.

Answer one repeatable research question: "What does this company depend on, what changed, and where is the evidence?" Make it a useful workflow to research companies, not a collection of decorative dashboard numbers.

## 6. Data dependency and measurable goals

V106–V109 original data work must continue in parallel: 348/500 saved prices missing, only 17/500 exact identity joins, no licensed public equity histories at last audit (21 Nov 2026), while 136/139 monitored daily comparisons were heuristically eligible, not official certified closes. 500/500 truly dated daily equity observations, rights-cleared historical charts, coherent original news and company relationships are acceptance targets, NOT present coverage claims.

Each release requires a PR, automated regression, visual screenshots, deployed-byte verification, and an issue update. Never purchase feeds or violate publication/retention rights without user approval.
