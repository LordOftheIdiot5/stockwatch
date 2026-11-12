# Stockwatch V4 — multi-page financial research UI

## Design & navigation

The homepage is a lightweight overview. Independent URLs share one sidebar, sticky top status and search control:

- `index.html` — overview, market breadth, movers, freshest research, sector performance, research modules
- `stocks.html` — all watchlist companies, sector/exchange search and sorting, saved favourites, sourced stock details
- `news.html` — up to 100 latest news items grouped by day, with company/sector/type/day filters
- `calendar.html` — existing sourced earnings/dividend events from V3, if available
- `compare.html` — existing V3 comparative stock analysis
- `spreads.html` — A/B share-class ratio panels, date-aligned historical series when available
- `shipping.html` — 30 route/vessel definitions, including Capesize, Newcastlemax and Panamax, with license-aware quote placeholders and data-series fallback
- `commodities.html` — metal and energy prices and clearly labelled proxies
- `shorts.html` — latest disclosed short positions with source links
- `health.html` — existing V3 scanner/source-quality dashboard

All pages use `v4.css` + `v4.js` for common navigation. V3 research pages also load `research.js` + `research.css`.

## News archival semantics

The V3 scanner's `scripts/build_research_data.py` continues maintaining a `data/news-archive.json` rolling cache (180 days, 20,000 items maximum). V4 additionally generates `data/news-latest.json`, containing **only the 100 latest** for the public news landing page. Those items are presented in UTC day groups. This cache **is not a permanent database**.

A Cloudflare D1 / SQLite schema lives at `database/0001_core.sql`. `worker/index.js` implements a read-only historical-search endpoint and an authenticated, idempotent ingestion endpoint. `scripts/push_archive.py` can send fresh source-linked headlines to the Worker only after its URL and secret are explicitly configured. No D1 deployment or permanent database backfill is performed by this package.

The older news archive **must not be described as durable** until the D1 binding, Worker route, ingestion secret and a successful post-scan push have been verified. For a production rollout, restore any available prior archives before pruning the 180-day rolling JSON file.

## Shipping & freight

`data/freight-routes.json` is a catalog of route definitions, vessel classes and price units. It contains no fabricated rates. The existing `data/context.json` contains public-market *proxies*, not directly quoted freight routes. Licensed quotes and historical route files (`data/freight-history/<route>.json`) may be displayed only if their metadata expressly sets `redistributionPermitted: true`, the code and unit match, and the provider licence permits public redistribution. Empty or unavailable series are shown as unavailable.

The Baltic Exchange states that its benchmark data is subject to licensing, including public redistribution: https://www.balticexchange.com/en/data-services/Methodology/market-data.html . Do not scrape third-party display pages to republish route figures.

Newcastlemax is a vessel class, **not** a Baltic rate identifier. The table differentiates it from Capesize route codes such as C3/C5 and Panamax code P1A.

## A/B relative value

Only identical-date prices from both listings are used to build historical A/B ratios. Absent a dated historical source, the graph shows a transparent empty state. The page retains the scanner's existing `stationary` and `drifting` flags and the latest ratio, reported variation and z-score, but deliberately does not issue definitive buy/sell signals.

Before any trading interpretation: verify dual-class economic rights, split and dividend adjustment, net trading costs, liquidity, market depth, eligible currencies and period-stability of any estimated stationarity. Historical ratio deviations do not guarantee convergence.

## Validation

```
python -m unittest discover -s tests -p test_research_data.py -v
python tests/test_v4_browser.py
node --check v4.js
node --check research.js
node --check worker/index.js
```

The browser test uses a clearly marked 12 Nov 2026 30-stock historical sample. Production uses the existing `watchlist.json` with 138 configured companies; any missing quote remains visible. Do not include `preview/` demo data or builder scripts in the deployed web root.

## Deployment safety

Treat V4 as a candidate layered onto the existing V3 draft. Do not overwrite the production scanner, its source integrations, GitHub Actions schedule, notification code, RSS, backtests or existing `data/*` snapshots. Merge after real-source smoke testing.

For static Pages, copy ten HTML pages plus `v4.css`, `v4.js`, `research.css`, `research.js`, and `data/freight-routes.json`. Update the V3 research builder to generate `news-latest.json`. Deploy only after verifying page navigation and the 138-company production watchlist. A persistent backend requires Cloudflare D1 setup separately.
