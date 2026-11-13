# Stockwatch official-data connectors

These integrations are additive and do **not** replace the 138-company market scanner, the Cloudflare D1 news archive, or the licensed-history checks.

## No API key required

Run `python scripts/open_data.py --mode daily` to collect official, dated, attributed observations from Norges Bank (USD/NOK and EUR/NOK), the ECB (EUR/USD), World Bank WDI (GDP growth and exports/GDP), Eurostat (HICP annual rates), and the public Finanstilsynet short-register API.

Every Monday and Friday the scheduled workflow also queries GLEIF and Brønnøysundregistrene for up to 12 names each per run. **Name-only results are candidates**, never silently promoted to verified issuer identities. We store no private personal records.

Output: `data/open-data.json`. Each item has the original source, observation date, import date, unit, frequency, and reuse caveat. Failed providers are reported independently; previous successful values are preserved but **not presented as fresh**.

## Optional registered APIs

**OpenFIGI:** API v3 is supported. The importer uses ticker + exchange MIC, or verified ISIN + MIC where available, and stores only unverified instrument candidates. Run the following in your own PowerShell, then paste the API key at the hidden prompt:

    .\deploy\set-official-api-key.ps1 -Provider openfigi

**ENTSO-E Transparency Platform:** registration is not the same as receiving REST API access. Per ENTSO-E, request API access via the Transparency help desk and generate a security token in your account. When available:

    .\deploy\set-official-api-key.ps1 -Provider entsoe

The ENTSO-E connector checks an authenticated NO2 day-ahead-price response without storing or publishing raw prices. Data-item and primary-owner reuse rights must be verified before any public price charts are enabled.

After adding either key, run:

    gh workflow run open-data.yml --repo LordOftheIdiot5/stockwatch --ref main

The daily official-data refresh also runs automatically on weekdays. GitHub Actions secrets are read only on the runner; **never put keys in frontend JavaScript, Git, screenshots, or chat**.

## EODData and FRED

EODData's account described as **personal use only** must not feed Stockwatch's public or commercial database. `scripts/eoddata_private_probe.py` remains only for permitted personal evaluation; do not configure its key as a production secret.

## Data catalog and reliability

Stockwatch Data Health reports per-provider connection status, last success, and any issues. The Commodities page displays dated official statistical charts when at least two real observations exist. Official interest/FX data are **not executable securities prices**, and trade-flow statistics are **not freight-rate quotations**.

Free datasets do not solve licensed historical A/B share chart or Baltic Exchange rate rights. Follow applicable attribution and dataset-specific reuse terms.

Official source policies:
- Norges Bank: https://www.norges-bank.no/en/topics/Statistics/open-data/
- ECB: https://data.ecb.europa.eu/help/getting-data-web-services-sdmx-0
- World Bank: https://data.worldbank.org/summary-terms-of-use
- Eurostat: https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction
- Finanstilsynet: https://ssr.finanstilsynet.no/api/v2/
- GLEIF: https://api.gleif.org/api/v1/lei-records
- Brønnøysundregistrene: https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html
- OpenFIGI: https://www.openfigi.com/api/documentation
- ENTSO-E: https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token

## FRED and EIA (free registered credentials)

Both connectors are implemented in `scripts/economic_feeds.py`. Initial series:
- FRED: DGS2 and DGS10 Treasury yields, DFF federal funds rate, UNRATE unemployment.
- EIA: Europe Brent crude (RBRTE) and Cushing WTI crude (RWTC) daily spot observations.

The new public `data/economic-feeds.json` contains only real dated observations, explicit source links and provider health. Failed updates preserve the old original observation timestamps. FRED data is not automatically licensed for redistribution: these initial series are from government-origin publishers, and additional series need rights checks. None are executable investment quotes.

**On your authenticated Windows PC, install the API keys securely:**

```powershell
git switch main
git pull --ff-only origin main
.\deploy\set-official-api-key.ps1 -Provider fred
.\deploy\set-official-api-key.ps1 -Provider eia
gh workflow run open-data.yml --repo LordOftheIdiot5/stockwatch --ref main
```

This stores `STOCKWATCH_FRED_API_KEY` and `STOCKWATCH_EIA_API_KEY` in GitHub Actions secrets. Do not paste them into chat or commit them. View import status on the Stockwatch Data Health page and dated oil/yield charts under Commodities.

Documentation:
- FRED API observations: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- EIA APIv2: https://www.eia.gov/opendata/documentation.php
