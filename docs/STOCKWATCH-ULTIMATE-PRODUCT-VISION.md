# Stockwatch — ultimate product vision and operating north star

**Status:** Product direction and staged targets, **not** a statement of implemented capabilities.  
**Approved:** Product goal requested 2026-11-21; the source-of-truth delivery trackers remain [master execution plan](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md), [ROADMAP](../ROADMAP.md), [design issue #165](https://github.com/LordOftheIdiot5/stockwatch/issues/165), [market-data rights #176](https://github.com/LordOftheIdiot5/stockwatch/issues/176), and [data/source quality #185](https://github.com/LordOftheIdiot5/stockwatch/issues/185).

## 1. The mission

**Build the most useful independent, evidence-first market-and-company intelligence workspace for understanding how the real economy connects to listed companies.** Start where Stockwatch has a real advantage—Nordic/European corporate information and unusually detailed energy, shipping and A/B-share analysis—then extend coverage globally, including the US and major Asia-Pacific exchanges when facts and rights allow.

The one-line product promise:

> **Follow a company, discover what drives it, explore its business relationships, and verify every material claim against dated original evidence.**

The primary question: **What changed? Which companies may be affected? Through which *documented* exposures? What is the source, timeframe, quality and uncertainty?**

This is neither a broker, guaranteed real-time price terminal, generic AI stock-tip generator, nor an index of many mostly empty company pages. **Charts make a credible research workspace; connecting markets, companies, real-world operating drivers and verifiable evidence is the enduring differentiator.**

## 2. Ultimate end-state: one connected research operating system

The end-state contains seven interoperable layers:

1. **Global market observatory:** exchange indices, equities, authorized historical/possibly delayed quotes, market breadth, sectors, geography, volume where lawful, sourced events and licensed interactive charting. Each unit, venue and session is correct; unsupported venues are explicitly unavailable.
2. **Company 360:** legal issuer and security/share-class identities, earnings, cash flow, debt, operating KPIs, filings, executives where sourced, news, company history, A/B classes and explicit missing-data states. Always distinguish issuer-level facts from an individual listed share class.
3. **Evidence-backed company graph:** customers, suppliers, manufacturing, distributors, competitors, ownership, shareholder capital, loans, contracts, joint ventures and sanctions/regulatory exposure *where verified*. Each edge has primary evidence, both counterparty identities, type/direction, effective and source dates, revision history, and confidence. Contracted amounts are not recognized revenue or paid cash. Goods flow, financial commitments and observed payments must never be conflated.
4. **Real-economy exposure engine:** energy grids, power prices, hydro, shipping lanes/vessel classes, freight costs, ports, minerals, industrial inputs, agriculture, inflation, rates, currency, trade data and geopolitical/regulatory context. Connect company operating exposure to these drivers when demonstrable; label unverified hypotheses separately.
5. **Intelligence workflow:** universal search and a guided research agent that can answer factual questions, surface source links, compare 2–4 issuers, display transparent scenario sensitivities and alert on *actual observed events*; preserve research context when navigating. AI answers must expose citations, timestamps, calculations and unknowns, and never assert causal stock movement from correlation alone.
6. **Personal research workspace:** saved watchlists, comparison setups, saved graph views, event subscriptions and research briefs, with transparent privacy controls. Notifications are useful only after robust source validation, deduplication and consent; do not advertise push/email alerts before delivery exists.
7. **Data and integration platform:** durable provenance-first private storage and **rights-cleared** public products. Public searchable catalog, descriptive metadata, schema/version docs, quality and lineage, permissions and requests; later authenticated APIs/downloads, access contracts, usage limits, billing and correction workflows when operational. The asset is normalized original research and data lineage, not assumed resale rights to someone else's feed.

## 3. The irreplaceable user journey

A visitor searches for a company (or an energy price, shipping route, mineral, supplier or event). In one coherent workspace they can:

- See **what is known as of what date**: instrument ID, last permitted price, company results, events and source-quality status.
- See **why it may matter**: operations, geographic/commodity sensitivities, suppliers, customers, ownership and peer links, all evidenced or clearly marked hypotheses.
- Explore **one or two hops of verified links** without replacing the current workspace. Trace goods, capacity, contracts, financing and actual payments as separate entity/edge classes; never invent cash amounts.
- Open an original filing, source dataset or methodology entry for any material observation; compare with prior dated versions and use an interactive **rights-cleared** timeline.
- Save the research view and receive a meaningful alert only after a verified triggering observation and source-rights checks.

Illustrative scenario (product design, not a factual claim): “A change in shipping rates or hydropower availability is observed. Identify the documented shipping/energy exposures of our saved companies, compare authorized prices and official operating disclosures, and show a transparent scenario sensitivity rather than a predicted return.”

## 4. The positioning

**Public explanation:** “Market intelligence that connects companies to the real economy.”

**First customer:** self-directed Nordic/European investors and independent analysts who want reliable issuer research, company links, market context and A/B-share analysis rather than simply another quote page. Future customer segments: maritime/energy researchers, financial journalists, corporate strategy, asset managers and approved API/data partners.

**Advantages to earn, not claim prematurely:**
- Integrated cross-domain research from Nordl Energy and Leivro, with separate source rights and records.
- A rich historical **company-evidence graph** linking filings, business partners, materials, energy/freight and revisions.
- High data integrity: exact issuer/security identity, last-known observations with true dates, source status, permission provenance, missing-data visibility.
- Accessible, attractive, high-density terminal UX with useful company journeys and working fallbacks.
- Transparent models: calculations, assumptions and uncertainty visible; no fabricated forecasts or transaction values.

Do not compete by claiming faster live prices or more worldwide securities without the licensed feeds and coverage to prove it.

## 5. Strategic focus and scope boundaries

| Build first | Build after gates | Explicitly out of scope for now |
| --- | --- | --- |
| Useful deep company profiles; functioning charts and watchlist; real issuer news/financial statements; Nordic A/B; shipping/energy exposures; verifiable research graph; excellent navigation and freshness | Licensed international price/history feeds; reliable event/price alerts; richer verified graph, scenario engine, usable source-dated API products; US/Asia expansion; paid analytics | Order execution, brokerage/custody, fabricated real-time signals, unlabeled AI market predictions, guessed company payments, unlicensed redistribution, mass thin pages, forced paid subscriptions without an active product |

Company relationships and event evidence should be sufficiently deep before expanding from an initial focused universe to 700 distinct issuers, then 2,000, then 5,000–10,000 scalable listing/reference capacity. Count **distinct issuers**, listed securities and A/B classes separately.

## 6. Source and system architecture

- **Identify:** canonical issuer ID, LEI when verified, security FIGI, ISIN, MIC, share class and local ticker. Candidate matches are review-only.
- **Ingest:** time-bounded official sources and permitted provider feeds. Record terms separately for acquisition, private storage, website display, public export and paid API use.
- **Preserve:** source URL or document locator, retrieval/publication/effective/observation times, timezone, units/currency, immutable raw evidence where allowed, content hash, revisions and corrections.
- **Normalize:** events, issuer facts, price bars, rate series, operating units, routes, site geography, entity/relationship edges and permissions into typed tables; no cross-unit interpolation.
- **Explain:** expose provenance, observation age, quality, error/fallback flag and methodology in the UI and exports.
- **Protect:** do not replace a saved prior valid observation with a failed fetch; do not render data as fresh just because a worker or Pages build succeeded.
- **Operate:** GitHub release and CI, Cloudflare D1/R2/Workers as approved, health metrics, bounded backfills, backup restore, anomaly review and provider alerts; least-privilege credentials and no public secret leakage.

## 7. Commercial model and data-product strategy

A durable model can combine:
1. **Free research and discovery:** indexed substantive company/sector pages, limited saved tools, dated open-data visualizations and relevant news with source links; earn search traffic and trust.
2. **Premium workflows, only when delivered:** deeper source-reviewed comparisons, alerts, saved graph scenarios, research exports and specialized shipping/energy/company exposure tools; genuine user value must precede a paywall.
3. **B2B data/analytics/API, only when authorized:** normalized instrument identity, company/source-lineage facts, permitted shipping/macro/energy indicators, verified relationship metadata and customer integrations. Contracts, rights, compliance, authentication, usage metering, deletion/corrections and SLA come before sale.
4. **Optional referrals/ads:** minimal and clearly separated; never distort research rankings or claims.

**Stockwatch can become a valuable data business, but aggregated third-party market prices and licensed shipping benchmarks are not assets it can resell merely because it stored them.** Distinguish original derived research, source-licensed redistribution and technical platform IP in every valuation/business discussion.

## 8. Product experience: the design is part of the goal

- Approved 1672×941 Stockwatch reference is the target **composition**: dominant real chart, sourced index strip, breadth, news, heatmap, map/coverage, real saved watchlists and task actions. Never copy fictional mockup numbers, geographic returns or invented holdings.
- Professional desktop terminal, fully usable on phones, readable at normal zoom, keyboard accessible and light/dark consistent across **all 19 routes**; no sprawling scroll-only company page or disconnected research route.
- One clear primary task per page with expandable technical evidence, units and freshness. Actions must work or be explicitly unavailable; no false “coming soon” buy buttons or fake API login.
- Preserve source-valid fallback, historical archive access controls and missing-data transparency.

## 9. Delivery phases and objective gates

| Stage | Outcome | Acceptance evidence |
| --- | --- | --- |
| **V115 now — Data Products credibility** | Honest source-linked data product descriptions; schema/metadata sample, actual availability, rights and limitations; direct inquiry path; no phantom endpoint | Real catalog loads; metadata-only download; request path opens mail client or Telegram; browser + Node tests and published-byte match |
| **V116 next — UI and launch quality** | Whole-site visual acceptance against approved layout and all 19 routes | Desktop/mobile/dark/light/keyboard/200% zoom; true source dates, zero critical failures; independently reviewed screenshots and deployed asset hashes |
| **V117–V120 — Company intelligence depth** | Verified issuer facts, customer/supplier identity, typed evidence graph, A/B and operating drivers | Real audited issuer profiles, evidence review/retraction process, identity correctness and before/after coverage scorecard |
| **V121–V124 — Market source coverage** | Improve strict completed-session prices, authorized history and meaningful global indices; no blank pages | Per-venue numerator/denominator, source permission receipts, scanner freshness, independently validated chart bars |
| **V125–V128 — Product workflows** | Research agent with citations, real alerts, saved workspaces, economic-sensitivity comparisons | User journey tests, verified alert hit/false-positive rate, privacy controls, no undocumented data in answers |
| **V129+ — Commercial platform** | Rights-cleared versioned API/exports and commercial pilots | Working auth and schema, explicit licensing, contracts, rate limiting, quality SLA, support/correction workflow, paying pilot only after actual delivery |
| **Long-run — Connected global graph** | Multi-market capital + company + trade/energy/shipping network usable by people and authorized systems | Verified multi-hop relationships, causal uncertainty labels, independently sourced updates, repeat usage and sustainable revenue |

Versions are **planning labels, not deadlines or claims of completeness**. Advance on evidence, not only passing automated tests or increasing feature counts.

## 10. North-star metrics (report as numerator, denominator, date and rights)

1. **Research task completion:** % of sampled users who can answer a defined company/economic-driver question and open its primary evidence, segmented by desktop/mobile.
2. **Useful coverage:** # distinct issuers with correct verified identity, an up-to-date original filing, source-dated price status, and at least one substantive operating/financial fact; separate counts for quote, news, history, relation and event.
3. **Price integrity:** completed-session comparable observations / monitored listings, by venue and price-display permission; separately report retained prior closes and unconfirmed/zero-volume rows.
4. **Relationship evidence:** independently reviewed live graph edges / candidate edges, with corrections and invalidated edges tracked; do not label inferred monetary amount as observed cash flow.
5. **Source health:** on-time successful ingestions and records with permissible publication, age histogram, stale percentage, incident time to resolution and historical restore verification.
6. **Trust/UX:** source-link resolution, error rates, page-level overflow, task flow completion, chart/history licence checks and 19-route visual audit.
7. **Business value:** returning relevant researchers, meaningful saved workflows, consent-based qualified B2B inquiries, successful authorized pilot deliveries, conversion and gross margin after feed/hosting costs.

**Targets to pilot (proposed, not achieved):** audit 50 deep Nordic/European profiles before broad expansion; achieve 100% evidence/source completeness within that deliberately small cohort; establish 5 repeatable company-to-driver research journeys; permit a commercial product only with a signed rights/compliance checklist and a functioning delivery test. Re-evaluate numerical targets each release rather than inflating directory size for marketing.

## 11. Development decision rule

Every feature must answer:
1. Which **real user question** does it help answer?
2. Does an original, legally usable source exist? What specifically can be collected, stored, displayed and redistributed?
3. Can the user verify *what*, *when*, *where*, *unit* and *uncertainty*?
4. What is the correct fallback when data is absent or outdated?
5. Is the workflow simpler than before, and does it work from Overview to detail and back?
6. How will we measure useful coverage, repeat use and quality?
7. Does it strengthen the durable unique data/relationship graph rather than just add another panel?

**No feature ships by hiding missing data, inventing a quote/event/revenue flow, or replacing a working page with a visually impressive but nonfunctional mockup.**

## 12. Resume protocol for every future work session

Read this vision, [the master plan](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md) and [ROADMAP.md](../ROADMAP.md). Check main commit, open PRs, GitHub Actions, last scanner source-health, rights registry and issue #165/#176/#185. Finish the lowest-numbered incomplete *measured* milestone. Implement on a branch, run unit + Playwright + visual + permission checks, merge only after passing and verify production bytes + scanner **separately**. Update the scorecard and issue with precise completed/incomplete evidence. Never silently declare a future phase already operational.
