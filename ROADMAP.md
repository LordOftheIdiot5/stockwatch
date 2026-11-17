# Nordl Stockwatch — locked product and engineering roadmap
Approved direction from product discussion, 2026-11-17. Geographic allocation and US seed selection are implementation defaults; revise explicitly when needed. This is the source of truth for targets, not a statement that every feature is shipped.

## Product
Build a company-centric financial intelligence platform, joining market observations, public company disclosures, operating metrics, industry economics, trade, ownership, news, financial statements and capital-market dynamics. Store every eligible observation with source, units, observation period, collection/publication time, revision and usage rights. Never imply that saving data grants resale rights. Keep private retention, public display and commercial export permissions separate. Preserve last-known dates and never fabricate data or silently substitute listings.

## Coverage
Count distinct issuers separately from venue-level listings, share classes and securities. 700 distinct issuers first, 2,000 public platform target, 5,000–10,000 capacity. 300–800 deep intelligence profiles first; standard research profiles for other issuers; broad searchable directory. No thin or misleading pages. Initial 700/medium-term 2,000 allocation: Norway 150/300, Sweden 150/350, Denmark 50/125, Finland 50/125, other Europe 100/600, United States 200/500. US allocation primarily domestic issuers; foreign-domiciled US listings are explicitly classified and counted once by issuer. Prioritize sector leaders and companies with observable operating drivers.

## Development versions
- V60–68: price recovery, inventory, reported heatmap, issuer freight, ownership, maritime trade, stock/freight analysis, sensitivity and visual validation.
- V69–71: permanent private archive, expanded official collection and last-known recovery.
- V72–74: equity coverage expansion, issuer operating histories, full data coverage/audit and exchange preflight.
- V75: reviewed Euronext trade-condition mapping; separate ordinary trades, corrections, non-price-forming observations and official closes.
- V76: Nasdaq Nordic bulk-file connector; validate actual schema and source rights.
- V77: exact cross-exchange reconciliation using ISIN, security FIGI, MIC and currency.
- V78: authorized daily equity archive; immutable source objects, revisions, retention controls.
- V79: delayed intraday updates within source permissions and scheduling budgets.
- V80: historical charts, heatmaps, production coverage and visual audit.
- V81: unified historical observation database and data catalog, revision-aware recovery.
- V82: redesigned company intelligence page with licensed business photography, responsive layout, market prices and history, actual operating data, financials, drivers, ownership, timeline, peers, evidence and coverage indicators.
- V83: sector-specific economic drivers and measurable exposure definitions.
- V84: evidence-backed company, ownership, supply-chain and exposure graphs; distinguish context from measured links.
- V85: rolling correlations and lead/lag studies using matched observations and publication dates.
- V86: US-specific capital and liquidity intelligence (Fed, Treasury curves, equity benchmark/sector returns, ETF flows, options, buybacks, short interest, positioning and earnings expectations where rights allow).
- V87: fundamental valuation and scenario models.
- V88: point-in-time walk-forward backtesting, corporate actions, survivorship bias, costs, benchmarks and error metrics.
- V89: calibrated probabilistic price scenarios, intervals and forecast journal, never guarantees.
- V90: unified Nordl Intelligence terminal and production quality audit.
Version order is a target; dependencies and validation determine merge readiness. Do not mark pending versions live; verify deployed release manifest and actual page assets.

## Company page design
Consistent responsive dark/light design. Compact hero with real issuer-specific photograph (ship, actual production facility, product or HQ), name, exchange, ticker, currency, date and price status. Main price chart and market context; business KPI cards; financial statements, business drivers, actual operations, peers, ownership/exposures, relevant news and event timeline; expandable technical evidence. Keep primary price and as-of time prominent. Images must not crowd out price/chart on mobile.
- Shipping: owned/operated (or historically associated, labelled) vessel, port or logistics operation; freight, fleet, volumes, backlog, bunker costs.
- Aquaculture: company farm/processing facility; harvest, salmon prices, costs.
- Energy: platform/refinery/field; production, commodity prices, hedges and costs.
- Industry: factory, equipment, production/backlog.
- Technology: actual product, chip, data center or HQ; revenue segments, demand, capex and supply.
- Finance: HQ; rates, credit, deposit/loan growth, capital and earnings.
Do not portray a generic asset as issuer-owned. If confirmed photography unavailable, use a labelled sector illustration or neutral no-photo layout. Prefer original company photo with explicit reuse permission or verified Commons CC0/CC BY/CC BY-SA, never arbitrary web thumbnails. Track asset ID, issuer, subject, source page, author, license URL, capture date if known, caption, rights review, transformations, alt text, locally optimized asset and attribution. Use performance budget (target 120–250 KB optimized hero, responsive variants, no automatic third-party image hotlinks). Respect trademarks, architecture and derivative license requirements. No implication of endorsement. Historic imagery explicitly dated.

## US market model
Do not use Nordic median as US baseline. Market-local exchange calendars and timestamps, US dollar returns, separate regional and sector benchmark excess return. Price is actual licensed market data, not a model output. SEC CIK identifies filer; ticker and MIC identify listing; FIGI identifies security. Start with the selected US-listed cohort in data/us-equity-seed.json. Reference-only until authorized price source; no zero prices or false signals. SEC EDGAR submissions and XBRL facts offer dated disclosed fundamentals: retain periods, units, accession, filed date, restatements; collect with declared contact and fair-access limits. US capital/liquidity inputs do not establish causal influence. No implied prediction ability without genuine out-of-sample tests.

## Data operations and release gates
Collect -> validate -> archive -> normalize -> connect -> publish permitted subset. Private R2 holds immutable content-addressed objects; no restricted raw records in public repo/site. Use dated source provenance, separate issuer/security/listing IDs, explicit currency and revision; never fill historical gaps with invented observations. Retain stale values only with dates and status. Archive model outputs with model version and prediction timestamp. Audit counts of distinct issuers/listings, current/missing prices, history, source failures, image coverage and licensing status. Tests for rights, matching, stale data, desktop/mobile, dark/light, accessibility and live release. No new paid subscriptions without approval.
