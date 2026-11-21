# V104b — Add daily company charts without replacing existing faster market data

**Owner requirement (2026-11-21):** Preserve **all** currently visible and working market graphs, sector heatmap, market map, market tape, global index cards, company/terminal charts, A/B tools, watchlist and data-health views. Existing prices with more frequent source updates must keep their current cadence and visible timestamps. New end-of-day closes are a **supplementary fallback/history dataset**, not a replacement or a forced frequency downgrade.

## Presentation contract — cannot be weakened in a future EOD integration

| Layer | Current behavior | New approved EOD behavior |
| --- | --- | --- |
| Frequent existing price observations | Scheduled weekday scans and dated current/retained observations remain unchanged | Do **not** disable the collector, reduce scan cadence or overwrite valid same-session/newer prices with an EOD value |
| Overview main chart, global-market pulse and all economic/FX charts | Keep all chart containers, graph controls, drilldown links and regional index data | Add an actual equity market primary chart only after a source provides authorized historical index/equity prices; never hide existing macro chart as a substitute |
| Sector heatmap (overview and Stocks & Sectors) | Keep visual tiles, working filters, hover/inspection, old observation/fallback labels, desktop/mobile layout | Retain scanner-derived movement/price-age inputs; never compute current-session heatmap move from a generic old EOD close or mix incomparable sessions |
| Company/terminal native chart | Existing available chart data and overlays remain accessible | Add **daily** dated line series from licensed EOD ledger; choose fast/latest existing observation for quote header if source as-of date is equal/newer. For 1D/intraday ranges keep proper intraday provider data only |
| No fast source quote | Show existing truthful unavailable/last-known labels | If actual authorized, verified newer EOD exists, display it as **Daily close** with its date/source; otherwise retain honest last known/unavailable |
| A/B ratios, alerts, breadth and signal intelligence | Continue explicit completed-session eligibility tests | EOD provenance must pass the same exact security/date/venue matching before analytical promotion; don't turn EOD archive existence into a fresh alert |
| Downloadable datasets & R2/D1 | Existing report/news archives continue unchanged | Store daily EOD observations separately and preserve their original sources, corrections and independent rights; use separate licensed public-display gate |

## Concrete precedence policy

1. Keep both datasets independent: **existing frequent source observations** (unchanged scanner JSON with changePct/spark/volume) and **licensed daily chart history** (EOD ledger with actual completed-session dates/venue/provenance).
2. For headline/latest price, when the existing source has a valid observation on the same or a newer trading date, **keep the existing price**. Never erase its original changePct, timestamp, priceStatus, volume, spark, or fast source.
3. When a verified, website-display-approved EOD observation is newer *and* exact instrument/venue/currency match is confirmed, it may fill a gap as an explicitly dated daily close. The original frequent-source record is still retained and continues collecting; it can reclaim priority on the next eligible observation.
4. A company stock history chart uses **only actual authorized daily bars** (and historical backfill if licensed). Never interpolate missing exchange sessions, derive invented candle opens/highs/lows, or force a 1Y chart out of one EOD observation. Two distinct days are needed for the first line segment.
5. The heatmap must stay **visible**, retain its category/filter controls and not break when price observations or feeds are missing. Only comparable source-dated changes can drive daily movement colors; old values should be visibly labelled.
6. Existing visual regression gates for homepage, heatmap and company/terminal pages remain mandatory at mobile/desktop viewports, alongside source/provenance and fallback tests. Run source outage scenarios.

## Code and validation

- `scripts/presentation_price_layers_v104b.py`: pure, side-effect-free **future adapter** for layered quote selection and authorized daily history; returns `existingObservation` and `licensedDailyHistory` independently, selects an existing quote on same/newer date, or newer EOD as an explicit dated fallback. It **does not** connect a provider or overwrite the existing UI/scan data; caller must establish actual permission and verified listing identity.
- `tests/test_presentation_price_layers_v104b.py`: scenario tests for current/same-day frequent price, older/newer EOD, separate EOD public display grant, exact listing/currency, data gaps, preserving changePct/spark, and static DOM/controller guard for existing heatmap and macro chart.
- Existing [V104a private EOD ledger](V104A-DAILY-EOD-CHARTS.md), [V102 source entitlement register](V102-SOURCE-ENTITLEMENTS.md), [master execution plan](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md).

**Important operational status:** No new daily market source, completed-session quote or company EOD chart became live solely through V104b. This release preserves current components and makes the additive source precedence machine-testable. A future UI integration still needs the license, actual data, verified identity and separate browser/visual proof.
