# Stockwatch official-data connectors

These integrations are additive and do **not** replace the 138-company market scanner, the Cloudflare D1 news archive, or the licensed-history checks.

## No API key required

Run `python scripts/open_data.py --mode daily` to collect official, dated, attributed observations from Norges Bank (USD/NOK and EUR/NOK), the ECB (EUR/USD), World Bank WDI (GDP growth and exports/GDP), Eurostat (HICP annual rates), and the public Finanstilsynet short-register API.

Every Monday the scheduled workflow also queries GLEIF and Brønnøysundregistrene for up to 12 names each per run. **Name-only results are candidates**, never silently promoted to verified issuer identities. We store no private personal records.

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

EODData's account described as **personal use only** must not feed Stockwatch's public or commercial database. `scripts/eoddata_private_probe.py` remains only for permitted personal evaluation; do not configure its key as a production secret. FRED is intentionally not connected until account/key approval.

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
