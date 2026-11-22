# Stockwatch P0 — Shipping and Offshore Intelligence expansion
**Adopted:** 22 November 2026 · **Owner priority:** immediate source/licence and shipping UX inventory; highest-priority *new product domain* after blocking V116 usability acceptance, before broad V117 enrichment. **Execution issue:** [#214](https://github.com/LordOftheIdiot5/stockwatch/issues/214). **Target:** [Shipping & freight](https://stocks.nordl.dev/shipping.html). This is a **work plan**, not a declaration that data, provider rights, shipping modules or rate histories are available.

## Product goal and current baseline

Build a real maritime/offshore intelligence workstation for a Norwegian/Nordic-first audience, with region-by-region vessel-dayrate evidence and the factors that make charter markets change: oil and gas capex, rig demand, vessel utilization, fleets, backlog, fuel, ports, routes, wind projects, shipping company financial results and macro prices. Connect every source-confirmed rate or operating event to its exact original issuer, vessel/rig type, geography, date and measurement basis. The differentiator is **rates + contracts + fleet availability + listed-company economics + original source**, not multiplying decorative dashboard cards.

Current code shows three trade segments (dry bulk, tankers, containers) with **30 route definitions and 0 publicly licensed route quotes** in the 21 Nov baseline. Existing useful views: USDA ocean grain freight cost indices (indexed, not USD/day), BLS deep-sea freight PPI (monthly), UNCTAD liner network connectivity (monthly index), World Bank annual TEU throughput, Ro-Ro cargo, dated company operating facts, cost scenarios, freight-company stock proxies, route search and a rights-gated history function. Preserve them. The page currently does **not** implement a genuine offshore-vessel/rig-market taxonomy or an authorized PSV/AHTS spot chart.

## Priority order and execution checkpoints

| Queue | Rank | Immediate deliverable | Evidence required before marking done |
| --- | --- | --- | --- |
| S0: audit, sources, licences | **P0 / start now** | Inventory current UI and source observability; classify rate vs index vs proxy vs hypothetical; compile ≥20 candidate sources with licence/price and acquisition modes | Rights matrix, dated evidence, source telemetry and 19-route UX screenshots; rate-denominator 0 is acceptable |
| S1: offshore model and navigation | **P0** | Offshore, Rigs and Offshore Wind workspaces; vessel/contract/rate taxonomy with source-status and detailed landing states | 4+ genuinely usable class groupings, mobile/keyboard and unavailable-state tests |
| S2: actual disclosed offshore facts | **P0 / first published data pilot** | Original issuer/regulatory quarterly average day rates, utilization, fleet and backlog **as originally reported**, ideally a few comparable periods | 10 verified allowable observations across ≥3 independent original issuers/official sources, original citations and rights records; otherwise publish a scoped audit only |
| S3: licensed charter rates and broader freight | **P1 / permissions gate** | PSV/AHTS fixtures where licensed; dry bulk, crude/product/chemical tankers, gas, container, Ro-Ro and car-carriers | All spot/period/Worldscale/TC equivalent quotes separated by unit, vessel class, basis, contract and region; no scrape/copy of restricted benchmarks |
| S4: maritime demand/asset drivers | **P1** | Rig & vessel utilization, contracts/backlog, offshore project and energy capex, orderbook, port congestion and shipping disruption context | Dated primary sources, clear utilization denominators, historical method, contract obligations not double-counted |
| S5: integrated research UX | **P1** | Rate/contract comparison, time-axis native charts, map filters and issuer-vessel-project research paths | 5 real source-to-conclusion journeys, compact desktop/mobile, accessible table alternative, one-click return to Stockwatch |
| S6: optional data products/alerts | **P2** | Durable rights-gated snapshots, versioned data schemas, timely alerts/derived measures and optional licensed APIs | Per-field archival/display/export grants, reconciliation, scheduled feed health, retractions, no paid service unless approved |

**Sequencing with other Stockwatch work:** S0 source-and-licence audit can run alongside remaining V116h critical accessibility/visual tasks; S1/S2 shipping should receive the next substantive development allocation, ahead of scaling V117 to 50 issuer profiles. V117's evidence standard still applies to all company/contract relationships. Do not skip V116's genuine 200% zoom and owner visual acceptance or unrelated production incidents.

## Coverage matrix — labels, not fabricated values

### Offshore vessels and rigs (lead priority)
1. **PSV / platform supply:** deck area (m²), DWT, DP capability, North Sea spot vs period term, quoted fixtures vs company average realized rates, date, currency, paid working days, fuel responsibilities.
2. **AHTS / anchor handling:** BHP, bollard pull, minimum equipment/DP class, UK/Norway/Brazil regional charter, anchor-mobilization vs routine supply usage.
3. **Subsea, IMR, survey, seismic:** subsea construction (CSV), ROV support, diving support (DSV), heavy-lift, pipe-/cable-lay and survey vessels. Never compare directly with PSV on an unqualified daily-rate axis.
4. **Drilling rigs:** drillships (generation and water depth), harsh-environment/deepwater semisubs, benign and high-spec jack-ups, active/stacked/recommissioning status; original contract term, optional periods, dayrate and operating days.
5. **Offshore wind:** WTIV/jack-up installation, SOV/CSOV, crew-transfer (CTV), cable-lay, heavy-lift and seabed survey; distinguish wind-project stage from equipment contracted/operating.
6. **Other offshore-linked:** shuttle tankers/FSO/FPSO where market economics/contract evidence exist; accommodation vessels, floating production, marine construction support, spill-response and rescue only when independently reported.

### Freight (extend existing categories)
7. Dry bulk — Capesize, Newcastlemax, Panamax/Kamsarmax, Supramax/Ultramax, Handysize; differentiate laden voyage cost vs time charter equivalent and cargo route.
8. Crude / products — VLCC, Suezmax, Aframax, LR2/LR1, MR, Handysize, dirty/clean/chemical, CPP/DPP; Worldscale vs TCE vs USD/tonne.
9. Gas — LNG, LPG VLGC/MGC and authorized ammonia/CO2 speciality carriers; engine type and route/trade duration matter.
10. Container and Ro-Ro — FEU/TEU slot price, vessel time charter, feeder trade, car carriers/PCTC, freight indices and contract spot distinct.
11. Support economics — VLSFO, MGO, LNG bunkers, emissions/ETS/CO2 allowances, canal dues, port charges, vessel OPEX, distances, tides/weather, voyage/waiting time, disruptions and charter cost sensitivity. Do not imply exact observed fuel bunker quotes from model defaults.

### Asset-market and demand context
12. Offshore field/rig exposure: Norwegian continental shelf well permits, active wells and fixed/mobile facility associations; project FID/capex; sanctioned US offshore wind projects and regulatory transitions, with original map metadata.
13. Issuer evidence: vessel counts, average realized dayrate, term-leading edge, utilization, revenue per vessel or day **only where accounting definition is supplied**, backlog, optional vs firm contract days, contracts by customer where disclosed, fleet acquisition/disposal and financing.
14. Shipping macro: UNCTAD connectivity/port TEU, Korea Customs freight spend, USDA vessel-rate indices, BLS monthly ocean transport producer prices, EIA oil/marine fuel where permitted, public port/canal statements, trade/commodity flows. Mark them **indices, costs, throughput or demand proxies**, not vessel fixture rates.

## Candidate data sources and legal gates

| Candidate | Information to validate | Important restriction |
| --- | --- | --- |
| **Original listed-company disclosures** (e.g. Tidewater investor releases / 10-Q, SEACOR Marine, DOF, Solstad, Odfjell Drilling, Subsea7, offshore operators) | Quarter-by-quarter *realized* rate, fleet size, region and utilization; charter contracts and backlog with dates | Verify facts, units and citation permissions per record. A published realized average is not a fresh daily spot fixture, nor does it grant reproduction of full reports |
| **Norwegian Offshore Directorate FactPages / API** | Official shelf facilities, rigs, activity, licence/project links and operators: https://www.sodir.no/en/facts/data-and-analyses/open-data/ and https://factpages.sodir.no/en | Check exact resource licence (NLOD where stated), update frequency and entity joins; **not** a PSV/AHTS rate feed |
| **BOEM offshore mapping/data** | US leases, projects, wells, wind planning/lease geography: https://www.boem.gov/renewable-energy/mapping-and-data/renewable-energy-gis-data | Verify per-dataset terms, effective dates and project status; cannot infer vessels contracted or project economics |
| **Baltic Exchange** | Cargo-route definition and licensable daily bulk/tanker/gas/container/FFA data: https://www.balticexchange.com/en/data-services/market-information0/indices.html | [Licensing + redistribution policy](https://www.balticexchange.com/en/site-services/data-policy.html) applies: website and API use require explicit rights. Public route descriptions are not permission to publish rates |
| **Broker/industry vendors** | Clarksons, Seabrokers, Fearnleys, Braemar, Kpler, Freightos: assessments, vessel fixtures, dry-bulk and tanker rates, asset values, rig/OSV utilization | Usually commercial licence; read-only sample or press article is not redistribution authorization. Document quote, fields, costs and contract restrictions before owner approval |
| **Official transport and energy indicators** | Existing USDA/BLS/FRED/UNCTAD/World Bank; Korea Customs, port authorities, MET Norway, NOAA/EIA for energy/weather | Units and cadence vary; do not relabel USD/index/TEU/quarterly operating metrics as daily USD/day charter fixtures |
| **AIS/ship tracking** | Vessel metadata and route position only where specifically permitted by provider | No crawling VesselFinder/MarineTraffic or exposing restricted AIS; nonlicensed global tracking not a release blocker |

**Verifiable example for first pilot:** Tidewater's September 2026 quarterly results include vessel-level/segment operating metrics and a *reported realized average dayrate*. This is original issuer evidence to inspect, **not a live PSV/AHTS spot benchmark**. Link: https://investor.tdw.com/news/news-details/2026/Tidewater-Reports-Results-for-the-Nine-Months-Ended-September-30-2026/ . Distinguish realized period, leading-edge term charter and market assessment. Extract only appropriately usable facts with source, accounting definition and as-of period.

## Proposed data contract

`offshore_asset`: canonical asset ID; IMO/MMSI only if verified and legally reusable; rig/vessel flag; asset type/class, owner vs manager/operator (dated), capacity/capability, flag, active/stacked/unknown, region, source IDs.

`marine_rate_observation`: observation ID; asset/class/region/route; rate kind `issuer_realized_avg | issuer_contract_disclosed | broker_spot_assessment | period_tc | tce | freight_voyage | index | modeled_scenario`; decimal value (nullable), currency; units `USD/day | NOK/day | USD/tonne | USD/FEU | USD/TEU | Worldscale_points | index | USD/ship_day`; source name/URL/locator; observation/period start/end and publication/retrieval times; fleet eligibility/count, minimum vessel spec, contract duration, gross/net, bunker/FX assumptions; rights flags individually for collection/retention/public display/API export and last verified time. Do not convert rates across incompatible units without a documented economic model.

`marine_contract`: issuer/company and counterparty IDs (verified), vessel/class/project, geography, report/award and service/effective dates, firm vs option days, gross contract value and value basis, disclosed cash receipts **separate** from backlog/award, review state, correction/retraction and exact citation. No guessed customer/finance flows.

`marine_source_health`: feed ID, latest successful download, latest underlying observation, cadence, source-age, count of comparable and stale observations, rate-vs-proxy vs unlicensed coverage counts, schema validation, licence expiry and explicit error classes.

Storage: existing approved immutable R2/D1 pattern for permissions-cleared private data; GitHub Pages only carries a small validated public subset. Never mirror vendor PDFs/raw bars or archive forbidden materials because they were reachable.

## Page layout and user journeys

- First screen: concise **Shipping & Offshore** title; tabs **Freight | Offshore vessels | Rigs | Offshore wind | Ports & logistics**; source-freshness and number of actual published rate observations split from indices/proxies; featured source-backed observed rates or clearly dated issuer averages. No empty quote ticker.
- Offshore: regional/class filters (North Sea default, global optional); separate *quoted dayrate* and *issuer average realized dayrate* panels; utilization, active fleet, source/link, update time and full table.
- Rigs: drillship/semisub/jack-up filters; charter economics and period duration, stacked supply, award/contract/option status with original notices.
- Freight: preserve current 30 definitions, category search, rate rights and cost calculators; link to actual permitted series when connected; add classes and bunker/canal inputs without fabricated price defaults.
- Wind: installation/CSOV/CTV/cable and official project sanction dates, country project maps and contracting exposure; not a fictitious live charter ticker.
- Context: honest shipping company/stock links and relevant Energy Nordl facilities/energy drivers when source-identical; geographic coverage map is not a map of live vessels unless tracked under licence.
- Five acceptance journeys: (1) North Sea PSV rate → original issuer reporting period → relevant listed company; (2) AHTS utilization/backlog trend → cited fleet disclosure; (3) drillship contract days/firm vs options → original rig-status report; (4) offshore wind vessel requirement → BOEM/source-linked project and company facts; (5) tanker freight definition → contract unit/bunker cost/dated quote rights → linked issuer.

## Engineering/release QA (mandatory)
- Verify count of **licensed current physical rates** separately from quarterly averages, historically sourced fixture datapoints, route descriptions, indices and stock proxies; show each numerator/denominator. 0 daily licensed rates remains valid.
- UTC/local dates and timezones, period/contract/region and charter rate basis cannot silently change; calendar gaps preserved.
- Source outages do not replace last known validated observations; visibly dated fallback is allowed when licence permits.
- Playwright visual audit at 320, 390, 768, 1024, 1440, 1672 and 1920 widths, both themes; keyboard/screen-reader names, genuine 200% browser zoom, no page-wide horizontal overflow; source/date/units readable and no giant empty decorative sections.
- Only merge after source/rights tests, price-unit and duplicate issuer/asset checks, cross-page navigation, full research release regression, upload/verify exact Pages SHA; verify data-feed freshness **independently**.
- Business gate: no paid vendor/contract commitment without owner authorization; do not claim future commercial API exports from internal observational data.

**Resumption protocol:** Check [#214](https://github.com/LordOftheIdiot5/stockwatch/issues/214) before any new shipping work; finish S0 then S1/S2 with measured evidence. Keep [#176](https://github.com/LordOftheIdiot5/stockwatch/issues/176) equity and source rights, [#185](https://github.com/LordOftheIdiot5/stockwatch/issues/185) dataset sources and [#205](https://github.com/LordOftheIdiot5/stockwatch/issues/205) V116 design acceptance open independently. Never claim planned series are already live.

## S1 implementation candidate — source-backed rates and genuine freight prices (22 Nov 2026, PR #216)

- Issuer reporting candidate: 18 Q2/Q3 USD/day observations, 11 Q3 latest-class rows, 3 original issuers (Tidewater, SEACOR Marine, Noble); specific PSV/AHTS/FSV/liftboat/rig subtypes, actual quarter, region, class, accounting basis and exact original source.
- USDA official public bulk-grain ocean freight candidate: **USD 72.75/metric tonne (U.S. Gulf → Japan)** and **USD 39.50/metric tonne (Pacific Northwest → Japan)**, for reported observation 2026-11-12 and report published 2026-11-19, source https://www.ams.usda.gov/sites/default/files/media/GTR11192026.pdf (Page 3). These are actual original U.S. government **route-specific grain freight figures**, not offshore USD/day rates or broad Capesize/Panamax Baltic routes. The USDA release prose says unchanged from prior week while the preceding report lists a differing Gulf endpoint; show no unverified week-on-week comparison.
- New public-facing UI panels with original source links, filters and same-class Q2 comparison (no fake chart bars or investor price substitutions); if a source file fails, the remaining Shipping page stays functional. Explicit **0 licensed daily broker spot rates**, so full market pricing remains a P0 sourcing/rights blocker.
- Validation: Node source facts, rights and values; Playwright 7 widths × 2 themes, real prices, source URLs, keyboard disclosures, no overflow and dual-source-failure fallback. Full 19-route audit and research CI are separately required.
- Important: This candidate is **not operational** until PR merge and actual Pages published-byte proof. Do not mark commercial price licences, current spot PSV/AHTS, Baltic/Braemar daily histories, Norwegian shelf contract quotes or broker-derived ship positions granted.

## V117t Norway/Europe + NavProfit reuse checkpoint (22 Nov 2026)

- Existing original Eurostat dataset `data/shipping-roro-traffic.json` already covers 10 European geographic selections including Norwegian Q2 2026 Ro-Ro cargo **1,161 thousand tonnes**, Sweden **12,166 thousand tonnes**, Denmark **6,041 thousand tonnes**, and EU-27 Q1 2026 **100,229 thousand tonnes**. Those are different reported quarters, not prices or issuer earnings; country values overlap EU totals. The dated importer `scripts/collect_roro_traffic.py` retains observations on source failure.
- Existing original World Bank/UNCTAD `data/shipping-ports.json` has Norway **862,983 TEU in 2024**, Sweden **1,640,487 TEU in 2024**, Denmark **935,848 TEU in 2024**. Annual total container throughput is not a current vessel movement, spot quote or direct freight payment.
- New `shipping-regional-v117t.js` lifts these **already collected** Norwegian/EU numbers into a high-quality geographic comparison and same-quarter year-over-year table, linked to existing full Ro-Ro charts. New direct original-source links: Kystverket's open Kystdatahuset API and data, SSB port calls table 09518 and maritime goods table 08923, and Eurostat. SSB API is CC BY 4.0; **no SSB numeric data is claimed ingested** until a validated importer is delivered. Kystverket historical AIS/open NLOD layers and restricted real-time API access are tracked separately. Never show mock AIS vessels as actual Norwegian coastal traffic.
- Audited [NavProfit](https://github.com/LordOftheIdiot5/navprofit): local-first AIS/fleet/voyage management, private invoices, estimate-versus-actual, bunker/FX and operational P&L. Reuse its concept of voyage financial cost breakdown in a **new independent source-labelled offshore charter model**, not private application state. NavProfit's hardcoded approximate port distances (including unconditional 2000nm unknown-route fallback), demo bunker prices and returned mock prices on provider failure are **not acceptable public source figures**. Its AISstream, OilPriceAPI and AI invoice credentials/users also never enter Stockwatch.
- `shipping-offshore-econ-v117t.js` uses original Q3 published dayrates as historical **illustrative inputs** and asks the user to enter billable days, calendar days, transit days, bunker assumptions, OPEX, port fees, commissions and contingencies. It shows gross revenue, cost components, contribution and break-even rate; not actual company P&L or spot charter market prices. Explicitly no storage or keys.
- Tests must verify original data and regions, mismatch/country aggregate disambiguation, scenario arithmetic, empty/invalid or unlicensed feed fallbacks, mobile 320/390 and full responsive matrix. Keep #214 open for Norwegian actual offshore daily fixtures/rig/spot rate permissions and SSB importer.
