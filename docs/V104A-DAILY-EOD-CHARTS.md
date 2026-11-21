# V104a — One authorized end-of-day close per trading session

**Checkpoint 21 Nov 2026; code preparation only.** This is a private incremental data importer, **not** a new authorized exchange feed or public chart history. Read [integrated roadmap](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md), [source rights register](V102-SOURCE-ENTITLEMENTS.md), [price-quality issue #176](https://github.com/LordOftheIdiot5/stockwatch/issues/176).

## Decision: daily close is the right first product

One *actual completed exchange-session* observation per symbol per trading day is enough for a daily line-chart, daily return and long-term performance. Two real dates can produce the first honest line segment; about 20–23 distinct trading sessions yield a month's normal weekday observations. An immediate 1-year graph needs an explicit **approved historical backfill**, not repeated polling or invented prior days. OHLC candlesticks need all four observed values and corresponding rights; a single daily close must not become fake OHLC.

**Exchange-specific sources**:
- [Cboe Europe policy August 2026](https://cdn.cboe.com/resources/participant_resources/Cboe_Europe_Data_Policy_August_2026.pdf), §6: EOD OHLC distribution exemption (no fee/agreement) is promising, **not** a delivered feed, verified retention rights or primary exchange official close; delayed trade records have a different policy.
- [Nasdaq Nordic EOD reports](https://www.nasdaq.com/products/data/nordic-baltic/nordic-end-of-day-reports): original listing identifiers, close and volumes. Contents redistribution licence described; product cost, delivery, archive, website and resale terms need confirmation.
- [Euronext Web Services](https://www.euronext.com/en/data/how-access-market-data/web-services): original EOD/historical API; [market data redistribution policies](https://www.euronext.com/en/data/real-time-data/pricing-specs-agreements/market-data-pricing-policies) require a separate licence for external display. Oslo Børs is not Cboe.
- Yahoo/Nordnet/DNB: original platform/account data access is **not** blanket permission for a commercial redistributable history; tracked as pending candidates in source rights registry.

## Implemented in this candidate

`scripts/eod_close_ledger_v104.py` accepts a bounded **preobtained, duly authorized provider JSONL** batch. No web scraping, broker login, implicit permission, market subscription, GitHub data commit or public API. It enforces all of:

1. Original [V102 rights registry](../scripts/source_entitlements_v102.json) is validated; named source's `productionCollection` **and** `privateRetention` must be independently approved with scoped evidence. Real registry currently denies all nine sources.
2. Exact source scope: quote MIC must match the provider product's supported venue(s). No official Oslo close from Cboe trades. `sessionVerified=true` does **not** stand alone: source review's `sessionCloseVerified` must also be true.
3. Explicit operator-reviewed mapping (`listingId` ↔ valid ISIN, canonical MIC, currency) with independent HTTPS evidence. Mapping must belong to Stockwatch's exact 500-ID directory on CLI use. No ticker suffix inference, FIGI candidates or name-only matches.
4. Valid positive decimal close, optional nonnegative integer volume, actual date and offset-aware provider publication time, original source link and session evidence. No future or synthetic gaps.
5. Unique close per source/listing/venue/session, idempotent replay. If a provider corrects a previous day's quote, the old price remains and the importer fails pending explicit correction review rather than quietly overwriting evidence.
6. Private **SQLite** ledger outside repository, durable source receipt hash. No public chart export by default. A separate read-only `chart_rows` operation requires the `publicDisplay` grant in addition to retention permission and returns data only after at least **two real session dates**. It does not write HTML or deploy data.

Run after source contract, exact mapping and provider input exist:

```bash
python scripts/eod_close_ledger_v104.py \
  --source nasdaq_nordic_eod \
  --batch /private/approved-eod-bars.jsonl \
  --listing-map /private/reviewed-listing-map.json \
  --private-db /private/stockwatch-eod.sqlite
```

**This command must fail today**: all real source permissions remain false. That is deliberate. We can connect a provider once it is actually eligible, without redesigning the collector.

## Completion gates
- [ ] Confirm product access and legitimate acquisition path (Cboe EOD / Nasdaq Nordic / Euronext Oslo); establish rights for production collection, retained daily history and external display separately. Ask before paying.
- [ ] Obtain exact ISIN/MIC/currency mappings for Oslo/Stockholm/Copenhagen/Helsinki and all 500 listings, with annual renaming and A/B classes.
- [ ] Build a source-native adapter and actual delayed-EOD publication detection; compare two completed local sessions against original provider and exchange calendars. Each source-specific batch must be validated rather than trusting a third-party CSV filename.
- [ ] Integrate approved batch to private R2 immutable objects and D1 row revisions; archive original delivered files **only if retention licence allows**, alongside content SHA and last-good restoration checks. This SQLite module is the regression-tested transaction prototype.
- [ ] Add explicit, rights-gated public export and wired company/native chart component using only approved bars, with as-of date, currency, venue, provider citation, gaps, daily returns only on comparable sessions and unavailable/stale state.
- [ ] Release after real fixture, CI, visual/browser tests, verified Pages asset checks and measured comparable-session improvement. Never call 500/500 daily closes operational until proven.

## Baseline and acceptance metrics
- 500 research listing IDs, 152 saved/348 missing; 139 monitored last-known prices.
- Last completed 2026-11-20 session: only **2/139** verified, **132 unconfirmed, 3 older, 2 no volume**. A market scan's timestamp is not the observation date.
- Licensed equity history: **0/500**. New module does **not** change that count until real rights-cleared provider data is supplied.
- Track completed daily sessions with eligible EOD close per MIC and issuer; number with 2+/20+/250+ authorized bars, last date, gaps, source entitlement and storage/website rights.
