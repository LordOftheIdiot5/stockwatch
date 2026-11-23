# Nordl Market Intelligence Layer — V121 execution plan

**Date:** 23 November 2026. **Status:** V121 Shipping evidence pulse in draft; cross-site ingestion and exposure graph not yet operational.

**North star:** translate the Nordl ecosystem's observations into defensible explanations of **what changed, in which market, over what period, and for which geography or company**. Show source strength, missing data, uncertainty and useful avenues for investigation. Never invent causes, shipments, prices, profits, trading alerts or forecasts.

## Evidence hierarchy

1. Original source observation: provider, measurement, unit, actual period, published/retrieved dates, original URL, licensed uses, any corrections.
2. Comparable change: only compare identical metric/unit/provider/entity and compatible reporting periods. Weekly to previous week, monthly to previous month, and seasonal cargo to the same quarter in the previous year.
3. Descriptive signal: arithmetic change + its original facts + period/source + explicit limits, not narrative guesswork.
4. Watch hypothesis: possible relationship marked unverified. Never label a correlated movement as causal.
5. Verified impact: only connect a market observation to a real operator, asset, company or contractual exposure after source-dated evidence shows the relationship.
6. Forecast or decision support: future stage after backtesting, full-rights review, out-of-sample validation, revision handling and well-calibrated uncertainty. Not part of V121.

## Already observable from snapshots retrieved 23 Nov 2026

| Series | Actual signal and comparison | Interpretation limits |
| --- | --- | --- |
| UNCTAD monthly liner network, Sep vs Aug 2026 | Denmark −6.15%, Sweden −3.66%, Norway +2.12% | Country shipping-network connectivity, not actual vessel movement or cargo demand |
| Eurostat Ro-Ro Q2 2026 vs Q2 2025 | Norway +6.12%, Sweden +3.44%, Netherlands +0.73% | Country main-port gross cargo weight; not carrier utilization or vehicle exports |
| USDA weekly ocean grain freight index, 18 vs 11 Nov | U.S. Gulf→Japan 184.97 vs 185.61 (−0.34%), PNW→Japan 187.65 vs 187.65 | Indices indexed to 2017=100, not daily Baltic spot charter quotes |
| World Bank WDI annual container throughput 2024 vs 2023 | World +6.99%, Viet Nam +15.92%, Norway −2.22% | Historical annual totals, not today's port-level handling |
| Wallenius Wilhelmsen Q3 vs Q2 2026 | Realized net freight +4.89%, volume −2.94%, backlog −10.77% | Three issuer-specific measures; none proves next-quarter earnings |
| USDA dated grain route indications, 12 Nov 2026 | Gulf→Japan $72.75/t; PNW→Japan $39.50/t | Different voyages and distances; not a valid arbitrage or weekly change |

Do not hardcode these results in production UI. Compute from the current stored dataset, preserve exact observation dates and reject stale/incompatible periods.

## V121 deliverables and testing

- Deterministic source-comparison engine in scripts/maritime-pulse-v121.mjs, with missing values rejected rather than converted to zero.
- shipping-market-pulse-v121.mjs and corresponding CSS: compact map shortcut that disappears behind an open inspector; full market-evidence desk below map with market filters, numerical observations, source links, original periods, method caveats and map/company navigation.
- Consume approved existing JSON: shipping-open, shipping-connectivity, shipping-roro-traffic, shipping-ports, company-operating-metrics, shipping-usda-ocean-rates-s1. No new scraping, redistribution, synthetic ships or licensed spot rates.
- Source-specific freshness: weekly <=30 days, monthly <=150 days, quarterly <=270 days, issuer <=210 days, annual <=1095 days. Older observations remain in original archive/research but are not promoted as recent market pulse signals. Annual 2024 evidence must be labelled historical.
- Node regression for exact comparable changes, same-quarter YoY, stale source gating, partial failure, source identity and non-causal language.
- Chromium at 320/390/768/1440/1920 in light and dark: no horizontal overflow, all 40 original port markers, no duplicated component, map interaction stays working, map preview hidden by inspector, 6 evidence categories with mocked test-only provider-shaped data.
- Gate on full research release tests, sitewide visual audit, Shipping V118/V119c tests, successful Pages deployment and byte parity of published Shipping HTML, JS, CSS and Natural Earth 1:50m assets.

## Cross-domain plan

**Shared observation contract (V122).** Source ID, source URL, rights, license, original locator, observed period, published time, retrieval time, revision time, metric, value, unit, frequency, geography level, exact entity/listing/IMO identity, data-quality status and retention/export entitlements. Store revisions and point-in-time provenance in approved D1/R2 infrastructure.

**Derived signal contract.** Input observation IDs, algorithm version, baseline IDs, per-unit comparison, vintage/freshness, sector/region, original source links, confidence about *data quality*, missingness, interpretation limit and review status. A derived fact must not inherit commercial export permission automatically from an open reference.

**V123 — Stockwatch Equity Change Desk.** Explain verified earnings, dividend, operations, A/B share-class and confirmed regulatory disclosures separately from share-price changes. Existing signals.json at the 23 Nov snapshot has marketPct=null and only three broad-market comparison samples; don't treat this as an exchange-wide market return. Existing manually checked company relationships represent disclosed links, not verified current cash flows or exposure weights.

**V124 — Energy Nordl changes.** Build reservoir anomalies relative to their seasonal distributions, regional power price and demand observations, weather/snow context, verified outages and project changes from NVE, MET, ENTSO-E and approved national sources. No assumed financial exposure until the exact owner/asset relationship is verified.

**V125 — Leivro changes.** Detect permitted price, availability, ENERGY STAR/EPREL efficiency, product lifecycle and ownership-cost differences where public commercial rights allow. Keep private Icecat identities and restricted source rows out of public intelligence. A Nordl parent-page feed can present a few dated, strongest signals from all three platforms.

**V126+ — Relationship and hypothesis engine.** Build verified company→asset→geography→commodity→metric edges, each with source and effective date. Separate observational patterns from causal conclusions. Backtest event detection, correct for reporting revisions/seasonality and calibrate false positives before issuing alerts or forecasts.

## Unresolved rights/data gates

Publicly redistributable full Baltic, Clarksons or Braemar daily shipping rates are not licensed. The Fintraffic AIS/BarentsWatch production vessel layer is not enabled. No verified comprehensive company-vessel-port ownership/cargo graph exists. A successful website deploy cannot justify claiming these features. Source-correct partial insight is preferred over invented completeness.

## Release order

1. V121 public Shipping Market Pulse (this PR).
2. V122 shared source/observation registry and server-computed historical signal archive.
3. V123 equity company/event evidence and exposure graph.
4. V124 Energy market changes.
5. V125 Leivro product/price change signals and curated Nordl cross-site hub.
6. V126 backtested anomaly ranking, calibrated alerts and only then optional prediction models.
