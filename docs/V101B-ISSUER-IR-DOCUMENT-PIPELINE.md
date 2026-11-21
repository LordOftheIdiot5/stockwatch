# V101b — Original issuer report discovery and document-data archive queue
**Date:** 2026-11-21. **Status:** pilot code only, not a complete ingestion/archive service. Follows [V101–V112 master plan](STOCKWATCH-MASTER-EXECUTION-PLAN-2026-11-21.md) and [#185](https://github.com/LordOftheIdiot5/stockwatch/issues/185).

## Why this matters
A Stockwatch company page should eventually show all the original annual/half-year/quarterly reports, earnings presentations, official financial calendars, material contracts, key operating indicators and verified relationships to customers and suppliers. Many source documents are on company investor-relations sites. Some issuer original ESEF/XBRL files can support machine-readable earnings/fundamentals, reducing dependence on news articles and second-hand summaries.

**Primary original sources verified 21 Nov 2026:**
- SALM.OL, SalMar — https://www.salmar.no/en/investor/reports-presentations/; annual, quarterly, sustainability and ESEF report links, separate presentations, original calendar https://www.salmar.no/en/investor/financial-calendar/
- AUSS.OL, Austevoll Seafood — https://www.auss.no/investor/results-webcast/; original annual report https://www.auss.no/investor/results-webcast/2025/annual-report-2025/ includes PDF and ESEF reference, and issuer calendar https://www.auss.no/investor/calendar/
- GJF.OL, Gjensidige — https://www.gjensidige.com/investor-relations/reports-and-presentations ; original interim and annual documents and investor calendar https://www.gjensidige.com/investor-relations/
- ANDF.OL, Andfjord Salmon — https://www.andfjord.no/ ; original integrated annual report/quarterly announcements. Cross-check issuer identity because ticker is legacy watchlist symbol.
- Another clear source example not yet in the monitored pilot: Nordic Semiconductor (NOD) https://www.nordicsemi.com/Investor-Relations/Reports including official historical APM spreadsheets, but must join its actual listing identity before adding.
- Oslo corporate reporting official appointed mechanism: https://newsweb.oslobors.no ; https://www.finanstilsynet.no/en/reporting/financial-reporting/ . US original issuer filings: https://www.sec.gov/search-filings/edgar-application-programming-interfaces .

## Implemented in V101b draft branch
1. `scripts/issuer_ir_sources_v101.json`: **four curated issuer-owned landing pages** joined to actual tickers in the currently monitored watchlist, with explicit allowed link hosts and false document-retention/display flags. It is not a verified complete list of the 500 issuers.
2. `scripts/issuer_ir_reports_v101.py`: default **offline** inspection; opt-in bounded (max six) HTTPS one-page-per-issuer discovery; explicit bots access check and fail-closed redirects and domain/port; response size cap, no login/session, no PDF fetching; extract link text/closest section, possible report type, potential year/quarter, source URL and deterministic id.
3. Fallback preserves already discovered candidate links if page is down. Dates/financial values are not invented: `publishedAt:null` and `fiscalYearCandidate` require document review.
4. `tests/test_issuer_ir_reports_v101.py`: network off, exact host/rights/robots and classification, duplicate handling and prior-snapshot preservation.
5. `.github/workflows/issuer-ir-discovery.yml`: manual proof run plus a bounded initial source-registry/workflow change probe on `main`; publishes candidate **metadata JSON as a short-lived CI artifact**; no public Pages data commit, no PDF archiving, no database or notification side effect.

Run local no-network schema:
```bash
python scripts/issuer_ir_reports_v101.py
python -m unittest discover -s tests -p 'test_issuer_ir_reports_v101.py' -v
```
A small first-source check also runs once when the reviewed discovery workflow or curated source registry changes on `main`. Future operator-triggered bounded crawls use the GitHub workflow with `execute_live=true`. The crawler honors robots rules and reports failures; a page accessible in a browser may still be unavailable to automation. This is deliberately not a recurring unrestricted PDF scraper.

## Next operational stages — DO NOT mark complete from candidate links
- [ ] Confirm issuer identities and disclosure domains against exact company/ISIN/LEI/MIC and original filing channels. Expand from 4 pilot pages to a reviewed 50 and then all 500 listed securities, grouping share classes by issuer.
- [ ] Manually review original source terms, copyright, robots and any valid exemptions; distinguish private analytical review, storage of the original PDF, display of short metadata/outbound link, derived factual financial values and selling a copy/API of the report. A public PDF is **not** automatic permission to mirror or resell.
- [ ] Archive originals in private Cloudflare R2 **only after retention permission has been confirmed** per source/format; content SHA-256, size, retrieval timestamp, URL, original publication and fiscal period, revision status, status check, deletion/expiry policy. D1 stores document index, issuer links, result metrics, provenance and storage rights.
- [ ] For authorized raw original document facts, extract ESEF XBRL first, then official structured PDFs: revenue, operating profit/EBITDA where definition clear, cash, debt, capex, shipments, commodity exposures, customer/supplier notices, dates, per share, dividends and guidance; each fact must reference document id, page/table or XBRL tag, reported unit, period, consolidated scope and amended/corrected status. Reject ambiguous facts. No full copyrighted prose mirror.
- [ ] Calendar: extract future issuer results dates directly from official calendars, with original URL, timezone, exact event type and preliminary/confirmed flag. Avoid showing last year's dates as next year's.
- [ ] Archive/replay health: expected reports vs actual, new vs revised content, failing IR pages, issuer coverage 7/30/365 days, stale snapshots retained; no empty page and no false fresh claim.
- [ ] Stockwatch UI: company page original-report list, fact table and linked source download; restricted documents linked out unless display rights confirmed, not copied.
- [ ] Integration: per-issuer counts to `data/listing-coverage-v1.json`, metadata-only company document index for Pages only after reviewed, private R2 and D1 integration and rights gate, performance and accessibility checks.
- [ ] Final production release requires branch full regression, browser and provenance checks; merge; optional successful manual collection artifact; reviewed safe public data; Pages exact file verification.

## Quote source investigation — Yahoo, Nordnet, DNB
- **Yahoo Finance** public terms: https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html include prior-permission restrictions on automated gathering, competing data archives and commercial reuse. Source providers may additionally prohibit copying/republication. Keep Yahoo last-known reference evidence distinct from an authorized public quote history. Do not turn a scraped row into licensed exchange historical price data.
- **Nordnet** official external API: https://www.nordnet.no/externalapi/docs/getting_started ; documentation demonstrates a possible *technical* market data feed, but Norway customer terms https://files.nordnet.no/pdf/nb-NO/allm_bestammelser.pdf state third-party price information is for the account-holder's use and not for onward distribution. Ask about permitted API, EOD licence, website redistribution, private storage, rate limits and costs.
- **DNB** online general terms https://m.dnb.no/en/markets/terms-and-agreements/general-business-terms-online restrict DNB-provided website information to personal non-commercial purposes. https://www.dnb.no/en/markets/terms-and-agreements states retail Oslo real-time visibility. A free display licence **for a retail customer** is not a Nordl commercial site permission.
- **Alternative EOD**: Nasdaq Nordic, Euronext Oslo, Cboe Europe with venue distinctions and separate display/storage rights in [V102a #186](https://github.com/LordOftheIdiot5/stockwatch/pull/186); this remains the right path to verified regular daily prices.

**Policy:** Keep researching all three as licensing opportunities, not as unapproved automated scraper targets. Licensing and user choice of a premium feed may be revisited if pricing/rights evidence justifies it. Source-verified financial facts and report dates are additive even while equity quotes lag.
