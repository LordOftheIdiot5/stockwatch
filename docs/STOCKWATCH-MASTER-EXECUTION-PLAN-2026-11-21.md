# Stockwatch — integrated master execution plan
**Checkpoint:** 2026-11-21. **Canonical design source:** `/Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png` in ChatGPT Library, plus [design issue #165](https://github.com/LordOftheIdiot5/stockwatch/issues/165). **Engineering backlog:** [ROADMAP.md](../ROADMAP.md), [data plan #185](https://github.com/LordOftheIdiot5/stockwatch/issues/185), [provider-freshness blocker #176](https://github.com/LordOftheIdiot5/stockwatch/issues/176). Historical versions are cumulative and not all numbered projects are delivered.

## Product north star
A fast, genuinely useful global **market and company-intelligence research terminal**. First view: sourced/date-stamped geographic market indices, dominant interactive chart, company news, market breadth, filterable heatmap, saved watchlist and contextual drilldown, in the approved dark Nordl visual system. Deeper routes: securities, A/B classes, company statements, verified customer/supplier and capital relations, freight, power, minerals and macro history. Every published price/event/relationship must carry source, actual observation date, period, units, quality and rights. Do not reproduce the mockup's fictional figures or label delayed observations live.

## Baseline — published source audit, as of 2026-11-21 04:33 UTC
- Research directory: **500 listing IDs** (not necessarily distinct issuers); **152/500** have a saved date-stamped quote, **348/500** missing; monitored cohort **139/139** saved dated prices.
- For Friday 2026-11-20, only **2/139** monitored listings completed-session comparable; **132 unconfirmed**, **3 older**, **2 zero-volume**; 0/12 A/B pairs comparable. A scan HTTP 200 or retained target-date label is not evidence of a newly published exchange bar.
- Of 139 monitored quotes, **1 MIC explicitly provided; 138 missing**. Broad directory audit counts **17/500 with ISIN+MIC**, **332/500 with FIGI+MIC** (candidate identities are not assured exact issuer/venue mappings).
- Directory: **213/500** sector; **100/500** exactly joined to archive news; **3/500** explicit fundamentals; **2/500** operating metrics; **0/500** descriptions; **0/500** licensed equity history.
- News archive baseline reported in V100 plan: 1,899 retained metadata records, 430 strong issuer links, 1,390 relevant non-duplicates. Independent 50-US-issuer SEC metadata cohort. **Zero source-verified upcoming earnings dates** in `data/events.json`.
- Three Taiwan official market index feeds are the verified homepage index foundation; they are not proof of global coverage. Existing 30 freight route definitions have **zero licensed route-rate observations**.
- V100 official Nasdaq Nordic RSS investor/exchange notices integrated and deployed. V98–V99 chart-first layout, watchlists and brand deployed; subjective approved-image parity roughly **65%**, not a test score.
- **Post-checkpoint 21 Nov update:** [PR #186](https://github.com/LordOftheIdiot5/stockwatch/pull/186) V102 EOD rights register (expanded to nine candidate products including Yahoo, Nordnet and DNB) and [PR #187](https://github.com/LordOftheIdiot5/stockwatch/pull/187) compact Source Freshness **merged** after their CI checks passed. [PR #188](https://github.com/LordOftheIdiot5/stockwatch/pull/188) first-party IR report discovery pipeline **merged** after full CI. None of these releases adds licensed price history or proves more same-session equities. Do not treat the informational entitlement register as a licence.

### V101 original issuer-report discovery — measured implementation, not full archive

A bounded [V101b report-link crawler](V101B-ISSUER-IR-DOCUMENT-PIPELINE.md) now exists on `main` and targets SalMar, Austevoll, Gjensidige and Andfjord original investor-relations pages. It requires robots compliance, whitelisted HTTPS sources, a bounded response and no PDF/ZIP/XLSX downloads. A real second proof [GitHub Actions #44888950720](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44888950720) completed successfully: **175 candidate source links across 4 issuers** (AUSS 150, SALM 18, GJF 5, ANDF 2), saved as short-lived private-run artifact `issuer-ir-link-candidates-v101`. These include landing pages and non-document links; they are **not** 175 verified document files. Further classification, human review, exact issuer identity, rights-verified document storage in R2/D1, fiscal fact extraction and company-page availability are incomplete. This extends, but does **not** complete V101. See [measured issue log #185](https://github.com/LordOftheIdiot5/stockwatch/issues/185#issuecomment-7060498833).

## P0 — shipping first, without waiting for every possible provider
### 0. Release hygiene, backlog and data health
- [ ] Review then merge/deploy #187 only after checking its actual revised 390/1440/1920px visual captures; verify Pages SHA and source CSS/JS asset bytes. Keep an honest compact session-verified X/Y figure with expandable UTC scan, unconfirmed count and full Data Health link.
- [ ] Review #186 (zero default entitlements) and merge after CI/source-policy check. Its permission matrix is a **review gate**, not a licence, invoice, signed contract, live data connection or automatic legal authorization.
- [ ] Treat #165 (design), #176 (source freshness/licensing) and #185 (new datasets) as living execution trackers. Every merged PR should link to measurable production evidence and list remaining restrictions.
- [ ] Keep weekday hourly market-window scanning, end-of-day recovery, two weekend maintenance scans, independent source-health checks and alerting; measure scheduled-versus-successful runs. Never describe scheduled polling as continuous exchange real-time pricing.

### 1. V101 — original company news, filings and verified issuer calendars
- [ ] Normalize original Oslo NewsWeb, MFN, Nasdaq Nordic issuer/investor notices, SEC EDGAR submissions and approved company IR feeds. Treat original regulatory filings, press notices and secondary commentary as **different evidence classes**.
- [ ] Strong issuer join by CIK / exact issuer code / verified ISIN-LEI-MIC/listing bridge. Deduplicate issuer, date, original URL, revision and event type; separate source publication from retrieval time. Preserve an old snapshot on an outage.
- [ ] Show 7/30-day verified-source coverage per exchange/issuer. Publish full article bodies only with rights; otherwise retain allowed fact metadata, short original title and outbound link. Multilingual coverage without altered quoted facts.
- [ ] Earnings, AGM, dividend ex-date and results dates require original-source dated evidence; show tentative vs confirmed when applicable and do not synthesize upcoming events from prior cycles.

### 2. V102 — rights-cleared daily equity prices (highest data blocker)
- [ ] Source-product register with **collection, private retention, public website display and commercial export rights** reviewed independently, evidence URL/contract clause, expiry, attributed field, permitted venue, currency, adjustment and fees. No approval inferred from access to a public webpage.
- [ ] Provider-by-provider due diligence in this order: **Nasdaq Nordic EOD** (Nordic/Baltic official), **Euronext Oslo/Euronext EOD** (Oslo/Europe), **Cboe Europe EOD** (alternative exchange trades, *not* Oslo/Nasdaq official close), **XETRA/Deutsche Börse**, then **US exchange/vendor and alternative provider** options. Compare true EOD vs delayed trades, vendor scope, fields, website redistribution, archive and cost; ask before buying.
- [ ] Exact identity mapping for 500 listings: exchange, canonical MIC, ticker, valid ISIN, issuer entity/LEI, share class, quote currency, security type, source instrument ID, corporate-action history. Resolve conflicts without name-only matching; A/B securities separate from issuer.
- [ ] Bounded authentic sample for **Oslo, Stockholm, Copenhagen, Helsinki, XETRA, Paris**, then other covered venues. Capture provider session date, actual bar timestamp, source date, last attempt, last success, previous source bar, response category, compliance evidence. No fabricated prices/fallback dates.
- [ ] Acceptance: publish a verifiable count of newly authorized completed-session daily observations by venue and corresponding right to web-display them, compared with current 2/139. If feeds/rights are absent, report blockers; do not mark complete.

**Official product leads (candidate, not active grants):** [Nasdaq Nordic EOD](https://www.nasdaq.com/products/data/nordic-baltic/nordic-end-of-day-reports), [Cboe European market data policies](https://www.cboe.com/data/market-data-services/document-library), [Euronext market data](https://www.euronext.com/en/products-services/euronext-real-time-data), [Euronext market data shop](https://live.euronext.com/en/datashop/core-market-data).

### 3. V103 — true exchange-session freshness and market signal eligibility
- [ ] Per-venue calendar, timezone, official trading day, holidays, local close and source-specific publication delay; use price bar date, not scanner execution timestamp.
- [ ] Diagnose distinct states: authenticated / unavailable / old provider session / currency mismatch / wrong instrument / missing volume / outage / rights missing / holiday. Keep last known price **visible but individually dated**; suppress stale % moves from alert, median *current-session* and A/B current-session calculations.
- [ ] Dashboard, health and archived snapshots publish exact denominators for monitored and entire research universe; show provider and exchange success separately.
- [ ] Test next session after a holiday, partial venue failure, A/B unmatched days, reused cached data, delayed market publish and clock/UTC rollover.

### 4. V104 — authorized long-term price-history warehouse
- [ ] Rights-gated, immutable **Cloudflare R2** source snapshots (checksummed/dated, only if retention granted), **D1** normalized instruments, bars, revisions, source permissions, retrieval history and archive pointers. GitHub Pages receives small licensed public data products, not secret vendor files.
- [ ] Native OHLCV chart with actual gaps, no interpolation; 1M/3M/1Y/5Y range only where history exists, currency, venue, adjustment method, timestamps, overlays and keyboard accessible tabular fallback. Document any derived return method.
- [ ] Simulate outage/rollback/replay and verify public last-known values are not overwritten by null/bad/out-of-order data; deny exports without explicit export rights.

## P1 — additional daily intelligence sources
### 5. V105 — US stocks and SEC
- [ ] Improve 50 known US seed issuer identities first: SEC Company Facts, submissions, 8-K/10-K/10-Q, insider 3/4/5, institutional 13F with amendments, dated provenance and per-field fiscal periods; expand cohort after exact mapping.
- [ ] Separate SEC public filing facts from **US stock prices**; obtain a suitably licensed EOD quote feed before plotting public price history. SEC official APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces. Respect fair-access and source terms.
- [ ] Normalize reporting quarters from explicit issuer fiscal periods and amendments, not simple calendar subtraction. Holdings are delayed positions; contracts are not cash already paid.

### 6. V106 — European financials, identity, fundamentals
- [ ] Official ESEF/XBRL, country regulator archives, Oslo exchange announcements and issuer financial statements. Preserve issuer, LEI, ISIN, MIC, fiscal year/quarter, currency/unit, accounting definition, filing revision and links.
- [ ] Fill 500-listing gaps in sector, official descriptions, shares outstanding, revenue, EBITDA, cash flow, debt, dividends and financial ratios **only where grounded**. Share issuer fundamentals across verified A/B listings without conflating their share economics.
- [ ] Improve GLEIF/ANNA and ESMA FIRDS identity joins with ordered corrections/cancellations; store unmapped or ambiguous instruments explicitly.

### 7. V107 — genuine global exchange-indices and geographic overview
- [ ] Keep Taiwan TAIEX/TPEx/Formosa as separate, dated native indices. Candidate coverage in source/rights order: Oslo OSEBX, Stockholm/OMXSPI, Copenhagen/OMXC25, Helsinki, DAX, CAC 40, AEX, FTSE, SMI, S&P 500, Nasdaq Composite, Dow, Russell, Nikkei/TOPIX, KOSPI, Shanghai/Shenzhen, Hang Seng, Nifty, STI, ASX, TSX, Brazil and other major markets.
- [ ] Every index requires official definition, display entitlement, source close, local session date, points and currency (if relevant), and permitted historical plot. **Never** present a regional macro proxy as an exchange index.
- [ ] Source-backed world map: venue locations, last permitted close and time; compare percent changes only for valid matching sessions and definitions. Explicit “Not connected” for unsupported exchanges. Responsive card strip and drilldown.

### 8. V108 — minerals, energy, macro, agriculture and freight
- [ ] **Metals/minerals:** USGS Mineral Commodity Summaries and subsequent surveys for lithium, copper, nickel, cobalt, rare earths, graphite, manganese, tungsten, silicon, gallium, germanium, antimony, phosphate/potash etc. Store reserves, extraction, production, imports/exports, countries and reference year; do **not** rebrand production tonnes as spot commodity prices.
- [ ] **Prices and macro:** EIA oil/gas/petroleum, World Bank Pink Sheet by-series permissions, ECB rates and FX, Norges Bank, FRED/BLS producer-price and shipping-industry indices, USDA grain/agriculture/transport costs, Eurostat/SCB/Statistics Norway etc. Distinguish rate, index, absolute price, proxy, forecast and timestamp.
- [ ] **Hydro/power:** re-use rights-cleared NVE, MET Norway and ENTSO-E electricity, reservoir, weather, generation and grid records through Nordl Energy with cross-site provenance and no unlawful redistribution.
- [ ] **Shipping:** evaluate Baltic Exchange, Braemar and Freightos **under explicit rights** for tanker/bulk/container route quotes; separate Capesize/Panamax/Supramax/Handysize, crude/product tanker and container routes. Current route definitions have no licensed quotes. Prioritize *actual* official Korea Customs monthly 40-foot container cost statistics (KRW per 2 TEU; country/region, not port spot quotes) and USDA transport cost indices, port TEU, EIA bunker fuel, fleet/route disruption. Source: https://www.data.go.kr/data/15129097/openapi.do. Build shipping-cost calculator only using clear units and dated inputs.
- [ ] Each source lands in its own temporal tables with source revision, unit, location and rights; never merge aggregate container costs, shipping spot quotes and economic indices into a single fake rate.

### 9. V109 — verified relationship and company-driver intelligence
- [ ] Extract source-dated supplier, customer, equipment procurement, distributor, financing, shareholder, contract and ownership links from regulatory filings/original reports. Require counterparty identifiers and a link back to precise evidence.
- [ ] Graph shares/materials/goods/services separately from equity investment, revenue commitments and cash transfers; no inference that one announcement proves an ongoing monetary flow.
- [ ] Show cross-company affected supply chains: semiconductors (NVIDIA and suppliers), shipping (freight/port/fuel exposed), energy producers, industrials, aquaculture and mineral constraints. Model hypotheses as hypotheses, not causation or trading recommendations.

## P1/P2 — design completion, product use and sales
### 10. V110 — reach approved full-width UI with actual data
- [ ] First fold: slim source health status, region-aware index strip, **dominant genuinely licensed market index or equity chart**, dated breadth and original news. Until then retain existing official EUR/NOK economic history clearly labeled as macro (do not mislabel Oslo index).
- [ ] Compact sector heatmap above the deep fold, with venue/sector filters, missing-data legend, fixed stale/price logic and company deep links; proper world markets map when indices are verified.
- [ ] Right-side rail holds relevant source-linked issuer news, real bookmarked companies, verified upcoming company events; no “target design” goals pane in public UI and no invented watchlist holdings.
- [ ] Expand native terminal indicators/crosshair/compare/chart ranges, A/B spread alignment and fees, company fundamentals/relationship pages, shipping units and timelines. Keep user-selected research inside app rather than losing sidebar/navigation on company drilldown.
- [ ] Full design QA: reference-image comparison at 320/390/768/1024/1440/1920; dark/light; mouse/keyboard/200% zoom; zero browser JS/asset errors and no page overflow. The approved image is illustrative only.

### 11. V111 — reusable and potentially sellable datasets
- [ ] Data catalog: instrument identity, permitted historical prices, source-linked news metadata, filings/fundamentals, commodity and freight indicators, company relations and licensing metadata.
- [ ] Separate collection, private retention, public display, commercial API/export and resale rights **per provider, field and record**. Publish schema, revision/date, country/units, provenance, quality and limitations.
- [ ] Versioned API with authentication, rate limits, usage reports, agreements, deletion/correction workflows, costs and source lineage. Avoid shipping private vendor datasets from Pages or exposing R2 credentials.
- [ ] Monetization model after rights validation: public/free market tools and SEO; paid alert/research workflows or authorized API/data subscriptions. No paid data source purchase without owner consent.

### 12. V112 — 500-listing quality and launch certification
- [ ] Publish complete 500-ID audit by exchange/group, deduplicated issuer, identity, last-known price, *current authorized price*, official filing, fundamentals, company description, historical chart and news. Separate 50-US seed.
- [ ] Compare every stat to raw source snapshot; test schedule/production health, Cloudflare R2/D1 restore, search, user journeys, phone/desktop rendering, source URLs, privacy and licensing; verify Pages actual deployed SHA and asset checksums.
- [ ] Pass/fail report, coverage deltas and unresolved provider commitments. Do not claim 500 current quotes, “live”, or commercial redistribution clearance without evidence.

## Execution scorecard: measure, never assume
| Metric | Baseline 2026-11-21 | Improvement gate |
|---|---:|---|
| 500 research listings with retained prices | 152 / 500 | Each new quote must map to exact listing and carry allowed source rights |
| Monitored stocks strictly completed-session comparable | 2 / 139 | Increase actual verified source dated observations per venue, not HTTP responses |
| Explicit monitored MICs | 1 / 139 | Increase verified MIC+ISIN joins and flag ambiguity, report all denominators |
| Licensed public equity history | 0 / 500 | Build real chart after explicit field/retention/display approval |
| Exact-join company news coverage | 100 / 500 | Increase original publisher/issuer-matched links and measure recall |
| Explicit structured company fundamentals | 3 / 500 | Add source-backed fiscal lines without inferred missing quarters |
| Sector tags | 213 / 500 | Increase official/reviewed sector mapping; provenance retained |
| Upcoming issuer dates | 0 | Import actual future filings/calendars; zero remains valid when unverified |
| Licensed freight route spot rates | 0 / 30 | Source/time/unit and route/contract matching before display |
| Approved design parity | ~65% subjective | Review screenshot-to-reference parity at target viewports; no invented market widgets |

## Mandatory contributor workflow
1. Prioritize an actual user information gap, not just an empty card or visual feature.
2. Identify official source/product, exact identity field(s), license and operational availability.
3. Prove a bounded original-source fetch; test schema/timezone/units and expected intervals.
4. Check and record permission for acquisition, archive, web display, API/redistribution independently.
5. Implement idempotent bounded collector and fail-closed parser; never erase a good last-known observation with bad data.
6. Store permitted raw evidence snapshots privately R2 with content hash; normalize facts/revisions into D1/approved tables.
7. Publish only allowed source-dated artifacts, with quality and fallback labels.
8. Add tests: unit, source-specific edge cases, missing/outdated provider, integration/browser at desktop+phone, full regression and visual audit.
9. Merge reviewed PR and verify actual public Pages asset integrity, scanner run and sampled production records; update ROADMAP and issues #165/#176/#185 with measured results.
10. Repeat; expand universe only when original cohort data health is improving. A company page with useful official research but no authorized quote can still be published with a truthful unavailable state.

## Immediate next work queue
1. Finish V100b #187 release and live audit, minimizing Source Freshness prominence while keeping the important warning truthful.
2. Finish entitlement preflight #186, then pursue primary EOD product access/rights and real per-venue quote diagnostic samples (#176), NOT another generic stale Yahoo retry.
3. Run V101 verified issuer-news/calendar expansion, exact matching and data continuity; update news coverage scores.
4. Prepare V103 freshness and venue identity joins while V102 provider terms are assessed; make real source proof gate for prices.
5. Complete V104 rightfully archivable price history then promote a genuinely authorized market chart to Overview; develop V107 world index and V108 freight/mineral datasets independently when original sources are confirmed.
6. Finalize V110 interface parity and V112 live QA against this scorecard, with V111 commercial entitlements tested separately.

**Status discipline:** Checklists are plans until code, tests, source rights and production verification independently pass. Revision checkpoints every two releases, or immediately after a chart/nav/data-source change.

## 2026-11-21 — Daily EOD + original issuer document execution checkpoint

**Completed engineering and tests; not yet a new price feed.**
- [#191](https://github.com/LordOftheIdiot5/stockwatch/pull/191) fixed a real V99 browser regression test assumption: a source-dated current observation is labelled `Reported`, not necessarily `Last saved`; comprehensive CI passed.
- [#189](https://github.com/LordOftheIdiot5/stockwatch/pull/189), squash `6e8c0d6504601514cbe728f6517f3d515721b5ed`, **merged** after complete [CI #44890347902](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44890347902) passed. Adds `scripts/eod_close_ledger_v104.py`: *one authentic completed-session daily close at a time* from an already-approved provider batch; exact issuer ISIN/MIC/currency, source MIC scope, actual report time, no conflicts on replay, private SQLite ledger outside public repo, explicit independent collection/retention/display permissions and 2+ real dates for a chart. It supports Cboe alternative execution MIC BATE/CHIX/CEUX **without** mislabelling those trades primary official closes. **All nine actual source rights still false.** No new live price data, R2/D1 production writes or public historical-equity charts were activated by this release. EOD provider delivery rights and a real reviewed mapping remain P0.
- [#190](https://github.com/LordOftheIdiot5/stockwatch/pull/190), squash `682127043811f2765ca987a7d28eed70034cabe7`, **merged** after complete [CI #44890328015](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44890328015) passed. The issuer metadata crawler now automatically creates a validated **report review queue** in the [real successful source-crawl run #44890454066](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44890454066). **175 original link candidates** across four issuers → **164 for document review** (81 direct file URLs, 7 opaque-download endpoints, 76 report landing pages), **11 other/irrelevant URLs excluded**. This is not 164 confirmed PDFs or archived documents.
- **Production release:** [Deploy dashboard #44890478842](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44890478842) succeeded for the #189 merge commit. A separate scanner run was pending when verified; no improved stock-session count is claimed.

**Actual next work, in dependency order:** A) Receive source access/contract clarifications from Nasdaq Nordic, Cboe Europe, EODHD or Euronext; verify original delivered EOD product and website display/private retention rights; no paid subscription without owner consent. B) Map verified ISIN/MIC/quote currency/primary versus alternative trading venue for the 500 listing IDs and implement one actual licensed daily adapter+R2/D1 receipts. C) Populate 2+ valid close dates per issuer (long-range charts require approved backfill), integrate native chart UI, date/venue/provider disclosures and browser QA. D) Verify 88 probable issuer document endpoints (81 file URLs+7 opaque) and 76 report landing pages; review original-file retention rights, then extract tagged ESEF/XBRL and verified source-linked finance facts. E) Check scanner source age and fallback by actual session before marking any daily history or fundamental dataset production-ready.

**Provider status 21 Nov:** Nov 20 original enquiries already sent to Nasdaq Nordic EOD, Cboe EOD and EODHD; earlier Euronext. Gmail search found Nasdaq case #04325385 acknowledgement, no substantive feed/rights responses. Cboe's MiFID public trade download page explicitly limits commercial use; its section 6 EOD OHLC exemption is a *different product* and not automatically a primary Oslo/Nasdaq official close. [Nasdaq Nordic EOD](https://www.nasdaq.com/products/data/nordic-baltic/nordic-end-of-day-reports) allows contents redistribution under its separate EOD license, subject to obtaining suitable terms/delivery.

