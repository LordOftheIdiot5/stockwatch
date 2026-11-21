# V105 — One real closing price per trading day, for every research listing

**Approved goal — 2026-11-21.** All Stockwatch research listings should ultimately receive **at least one correctly identified, date-stamped and display-authorized exchange-session price per local trading day**, with the existing more frequent price sources retained unchanged. This is a **coverage target, not a statement of live 500/500 service**.

## Baseline (actual GitHub published data, 21 Nov 2026 10:06 UTC)

| Coverage | Current |
|---|---:|
| Research listing IDs | 500 |
| Dated last-known prices | 152 (139 monitored scanner + 13 A/B pair observations) |
| No saved price | 348 |
| Dated on last completed common comparison day 20 Nov | 150 (includes pair references; not proof of official exchange close) |
| Monitored scanner session-comparable by conservative heuristic | 136 / 139 |
| Monitored exceptions | 1 old, 2 zero volume |
| Explicit combined ISIN + MIC in 500-ID inventory | 17 / 500 |
| Publicly licensed equity histories | 0 / 500 |

**Do not compare the now-improved 136/139 monitored heuristic result to the whole 500-company universe.** There are **361 research listing IDs outside the monitored scanner**: 13 hold dated A/B reference observations, 348 still have no saved price. Price and history rights, exact venue identifiers and archive availability are distinct gates.

## Implementation in V105

1. `scripts/daily_price_coverage_v105.py`: **read-only original-source data-quality auditor**, no network requests. Reconciles exact IDs of existing `listing-coverage-v1.json`, `signals.json`, `source-health.json` and the V102 market-data entitlement register; refuses mismatched batch times, duplicate listing identities, inconsistent market-quality denominators, forged future observation dates or inconsistent source rights.
2. `data/daily-price-coverage-v105.json` generated **after every existing scan/audit**, with 500-ID total, by-venue and by-cohort price coverage, dated vs missing, common-target-day counts, strictly labeled existing monitored heuristic quality, exact-ID coverage and authorized-history counts. An official EOD close certification is **not estimated**; unavailable is represented as null.
3. `data/daily-price-recovery-v105.json`: metadata-only per-listing work queue for missing/older/pair-only observations, exact identity evidence and rights-cleared history. It has no price values or vendor bytes. Never automatically request, scrape or bypass access restrictions.
4. Data Health page presents a compact six-metric scorecard and exchange table, with source-date caveat and outbound recovery queue link. **No changes** to the overview, global market pulse, heatmap, existing native company chart, alert logic, existing higher-frequency scanners or source cadence.
5. End-to-end CI: original 500-ID reconciliation tests, rights boundary tests, previous scanner preservation tests, frontend syntax and 390px/1440px browser render/screenshots.

## Acceptance and end-to-end next steps

- **V105 (this release):** automatic truthful coverage and prioritized gap dashboard for every one of the 500 listing IDs. This **does not claim that all 500 prices have been obtained**.
- **V106 security identity:** exact legal issuer, security ISIN, trading venue MIC and currency for the full target universe, with provenance; resolve ticker migrations and A/B classes separately. The exact identity coverage is currently 17/500; EOD licensing does not solve identity.
- **V107 source products:** obtain collection, private archive, public display rights and actual usable EOD deliveries for primary Nordic/Euronext/XETRA and separately Cboe alternative venues, then US/other exchanges. Review daily EOD licensed source candidates per venue and do not pay for subscriptions without permission. Keep Yahoo/Nordnet/DNB retail data outside any unapproved public archive.
- **V108 operational daily snapshots:** implement one bounded, provider-approved daily close for each verified listing after its own trading session, with exchange holiday, timezone and publication schedules. Write immutable licensed evidence to private R2 and normalized versioned close + issue flags into D1. Detect missing sessions and allow bounded next-day source recovery, **not** arbitrary increasing request rates or fabricating gaps. Rejected sources must produce a clear outage/permission status, not delete previous data.
- **V109 real graph coverage:** two observed licensed dates yield a first line segment, 20+ trading sessions yield useful monthly history, and 250+ real/approved backfill gives approximately one-year charts. Preserve native chart/heatmap/compare A/B tools and graph overlays. Existing higher-frequency prices always remain higher priority on an equal/newer source date.
- **V110 measurable acceptance:** per listing and venue: coverage of exact **completed local trading sessions**, date of last eligible authorized close, days missing, source provider, source quality, history depth, source rights, report timestamp. Target at least 1 verified eligible bar per trading day on all 500; no 100% claim without source rights and production proof.

**Cadence:** keep the existing weekday hourly 06:05–17:05 UTC market scans, weekday 22:20 UTC completed-session recovery and two bounded weekend checks. A successful scanner execution or target-day label alone is not exchange-session certification. The added audit runs immediately after the existing price inventory and before publishing its artifacts; it cannot change quote data or scan frequency.

**Visual guarantee:** retain the present sector heatmaps, globe/index market pulse, source freshness, macro/FX graphs, company and native terminal charts, smart/frequent data streams and watchlist. The daily EOD source is an additional line-history and permitted fallback layer only; see [V104b presentation rules](V104B-PRICE-LAYERS-VISUALIZATION-CONTRACT.md).

See also [master plan](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md), [source rights blocker #176](https://github.com/LordOftheIdiot5/stockwatch/issues/176), [dataset roadmap #185](https://github.com/LordOftheIdiot5/stockwatch/issues/185).
