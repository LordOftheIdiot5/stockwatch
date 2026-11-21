# Stockwatch V102 — European EOD source rights and identity preflight

**Audit date:** 2026-11-21. **Status:** candidate-source evaluation; **zero sources approved for new production collection, retention, display or commercial export** by this work. This document is not a legal opinion or contract confirmation.

## Why this comes before new equity feeds

At the last audited `main` scan on 2026-11-21 at 04:32 UTC, 139 of 139 monitored listings had retained last-known observations, but only **2 of 139** passed strict completed-session comparability for 20 November; 132 were unconfirmed, 3 older and 2 zero-volume. **Only one of the 139 watchlist entries had an explicit MIC.** Yahoo chart transport returned successfully for most symbols even while its latest daily bars were generally dated 19 November. Repeating a successful HTTP scan does not fix upstream session availability, venue identity or public redistribution.

The register in `scripts/source_entitlements_v102.json` is machine-readable, audit-only product metadata. `scripts/source_entitlements_v102.py` implements an explicit **deny-by-default** preflight. No new equity price ingest path invokes it yet; a future adapter must integrate the check at collection, archive, display and export boundaries, alongside per-instrument identity, actual original trading-session timestamps and source-specific contractual review.

## Verified source-policy findings

| Source / product | Public source evidence | Important restriction or limitation |
|---|---|---|
| Cboe Europe EOD OHLC | [2026 Cboe Europe Data Policy, §6 (printed p. 11)](https://cdn.cboe.com/resources/participant_resources/Cboe_Europe_Data_Policy_August_2026.pdf) | EOD OHLC **distribution** is not subject to a fee or Data Agreement under the cited policy. **Do not transfer that exemption** to minute-delayed/historical transparency trades. Verify exact product, delivery, licence scope, venue and qualified daily fields. Cboe is an alternative execution venue, not a primary-market official close. |
| Cboe Europe delayed trades | [Cboe delayed transparency portal](https://www.cboe.com/markets/eu/equities/transparency-data/) and the same policy | The policy separately requires an agreement for external redistribution of delayed/historical data, even where access is free. Aggregated daily trade files are not automatically certified closing prices. |
| Nasdaq Nordic Equity EOD | [Nasdaq product description and Nordic EOD licence](https://www.nasdaq.com/products/data/nordic-baltic/nordic-end-of-day-reports) | The described licence covers redistribution of **report content**, not redistributing complete delivered files. Subscription/delivery, display, historic storage and commercial/export terms still require confirmation for Stockwatch. Reports identify ISIN/ticker and trade prices. |
| Euronext / Oslo delayed trades | [Euronext trade-files terms](https://marketdata.euronext.com/data-reporting-service/trades-file) and [data policies](https://www.euronext.com/en/data/real-time-data/pricing-specs-agreements/market-data-pricing-policies) | Free delayed download is not blanket commercial distribution rights. Terms require an agreement for commercially beneficial distribution, and trade reporting may include conditions/corrections; it is not automatically an official auction close. |
| Euronext official-close product | [Euronext market-data offering](https://www.euronext.com/en/products-services/euronext-real-time-data) | Product/delivery and separate official close semantics, historic use, display and export licence still unresolved. |
| Xetra delayed transparency | [Deutsche Börse delayed service](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Delayed-data) | 15-minute delayed minute records remain available only until midnight of the following business day. Further commercial reuse and a verified official-close product remain unconfirmed. |

**Source interpretation is provisional.** Market venues may change terms; check the currently applicable contract/policy before enabling a provider. Public access and a favourable EOD policy provision alone are not enough to certify the exact fields, archive permissions and proposed subscription-free commercial website.

## V102 gate and use

The four independent capabilities are `productionCollection`, `privateRetention`, `publicDisplay` and `commercialExport`. All are `false` now. The registry refuses unknown sources, malformed original HTTPS references, incomplete capability matrices and approvals not tied to the exact source ID, named product and precise capability set. A truthful permission register **does not itself license data**: reviewed evidence must be secured and matched to terms, source, fields, venues, usage, correction policy, dates and plan before any flag can be changed.

Dry-run:

```bash
python scripts/source_entitlements_v102.py
python scripts/source_entitlements_v102.py --source cboe_europe_eod --capability publicDisplay
python -m unittest tests/test_source_entitlements_v102.py
```

The second command currently exits nonzero by design. This does not disrupt the existing reference scanner or publish new values.

## Next acceptance gates

1. **Product access and semantics:** For Cboe, inspect an actual provider-delivered EOD product and verify ISIN, MIC, currency, qualified trade/correction flags, session close and unique venue identity. Do not assume the existing transparency CSV is the exempt EOD product.
2. **Source-specific rights:** Confirm whether separate *collection*, *private historical retention*, *free website display*, *commercially beneficial display*, *exports* and *derived analytics* are authorized for the exact delivered product. Store review reference securely; never put confidential contracts or credentials on Pages.
3. **Instrument joins:** Complete verified ISIN+MIC+currency and qualified official-close/venue-session mapping. Current watchlist MIC gap is 138/139; do not infer from suffixes.
4. **Bounded provider probe:** Compare the same instrument/date under 3-month versus 1-year/exact-window responses; record response timestamp, bar date, provider and status **without public price values**. Existing `scripts/price_provider_diagnostic.py` provides a narrow precedent.
5. **Rights-gated adapter and test:** Only then connect a provider into scoped archive/display pipelines. Test missing entitlement, expired/superseded source terms, timezone/holiday, corporate actions, no volume, provenance loss, data gaps and retractions; deploy and verify live release checks before claiming V102 or V103 complete.

**Tracking:** [Data workplan #185](https://github.com/LordOftheIdiot5/stockwatch/issues/185) and [price-quality issue #176](https://github.com/LordOftheIdiot5/stockwatch/issues/176). V102 remains **in progress** until exact delivery and approval evidence exists; these files are only a reviewed baseline and a defensive testable gate.
