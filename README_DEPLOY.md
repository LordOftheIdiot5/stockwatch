# Stockwatch V4 release gates

## Production deployment
- Current app uses GitHub Pages (`stocks.nordl.dev`).
- Shared ten-page frontend reads the scanner's real JSON; preview/demo data is NOT deployed.
- New news metadata is saved in permanent Git-versioned month files (`data/news-store/YYYY-MM.json`) generated hourly. Historical dates from before enabling archival cannot be recovered from `seen.json` keys.
- Cloudflare D1 SQL is NOT active until the database, Worker binding, and secrets are configured. The Git-backed archive provides a working on-demand fallback.
- A/B historical and freight chart values only display from a provider whose license explicitly permits public redistribution, via `scripts/import_licensed_history.py`. Free Yahoo closes from the scanner do NOT imply redistribution rights.
- All stock, spread and shipping interpretations need primary source and unit, currency, adjustment, fee and liquidity checks.

## Optional Cloudflare D1 setup

Create the database with `npx wrangler d1 create stockwatch-research`, bind it to a Worker as `DB`, apply `database/0001_core.sql` using Wrangler, then set `NEWS_INGEST_TOKEN` as a Worker secret. Configure GitHub secrets `STOCKWATCH_ARCHIVE_URL` and `STOCKWATCH_ARCHIVE_TOKEN` only after verifying the ingestion endpoint. Never commit credentials. Detailed configuration: https://developers.cloudflare.com/d1/get-started/

## Required validation

Run `python -m unittest discover -s tests -p 'test_*.py' -v`, `node --check v4.js`, `node --check research.js`, `node --check worker/index.js`, and test navigation with the full 138-company watchlist before production promotion.
