# Stockwatch Final Research Upgrade — 13 November 2026

This release augments the functioning V4 multi-page site, Cloudflare D1 news
archive, 138-company watchlist and recurring GitHub scanner. It deliberately
does **not** claim licensed Baltic Exchange prices or public redistribution of
EODData personal-use records.

## 1. A/B share intelligence

- Interactive **A→B/B→A conversion calculator** using actual latest scanner
  A/B prices, configurable two-leg commission, slippage and minimum fees.
  Results show estimated acquired shares, cash remaining and execution drag,
  with a clearly labeled one-year *reference mean*, not a buy/sell call.
- **In-page threshold watch** for each pair: 1.0/1.5/2.0/2.5σ, saved in the
  user's browser. Conditions only trigger for current stationary candidates.
  No implied automated email or trading execution.
- The existing licensed-history chart remains available for authorized daily
  A/B closes. If absent, the display can use **new, actually observed daily
  A/B ratio snapshots** accumulated from each scanner run. These start at the
  date collection begins; no one-year price history is reconstructed from
  summary statistics. Commercial reuse of derived datasets still requires
  checking upstream rights.

## 2. Higher-quality company news

- Conservative issuer classification (`issuer_code` / explicit company mention /
  `review`) and deterministic headline-level duplicate detection within 48h
  for the same ticker. Preserves all raw archives in Git + D1.
- Filters by issuer confidence, sector, filing type, topic and UTC publication
  day. The initial page examines the 100 latest article records; filter
  Relevant by default; other matches remain discoverable.
- Search the live D1 archive by exact ticker, returning source-linked metadata.
- The scanner publishes an inspectable `news-quality.json` report.

## 3. Freight analytics

- Compare up to four routes by vessel class and correct unit.
- Explicitly refuse false USD/day vs USD/tonne vs Worldscale comparisons.
- Existing 30-route catalog persists; authorized historical route charts load
  only from verified source files. Shipping ETFs remain labeled **proxies**.
- Data health now reports licensed route-history coverage.

## 4. Quality and data provenance

- Fixes the stale `scanAgeHours` reading: the browser recalculates age using the
  actual latest scan timestamp.
- Cloudflare D1 article counts stay live on the Data health page.
- Adds source-quality and dataset-coverage summaries, a 138-issuer listing
  directory and evidence records for identified ISINs.
- Adds `source-registry.json` of official/open/paid feeds and restrictions.
- Fixes `PERR.PA` → `ALPER.PA` based on 2026 Euronext Growth migration and
  unchanged ISIN `FR0000061459`; does not fabricate a price if Yahoo fails.

## New files created during each scanner run

`data/news-quality.json`, `data/issuer-identities.json`,
`data/spread-observations.json`, `data/dataset-catalog.json`.
These all have documented provenance and explicit limitations. The original
news files, ticker data and scanner schedules are preserved.

## Validation

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_worker.mjs tests/test_final_js.mjs
node --check v4.js
node --check research.js
```

Run a fresh scan to build new datasets and refresh quote coverage. After the
next successful scan, check the public JSON and D1 health endpoints.

## Limitations and next licensing decisions

Historical raw OHLCV series still require a compliant source with display
rights. The historical A/B chart is not backfilled by assumption; the derived
snapshot series grows forward, one real scanner observation per UTC day.
Direct Baltic route rates and history remain unavailable until a suitable
commercial licence is executed. Sveriges Riksbank and Norges Bank open data
are documented as candidate datasets rather than silently presented as live.
