# Stockwatch V4 — release and data integrations

## Current state

- Frontend deploys through **GitHub Pages**, with the V4 pull request on a separate branch.
- The Git-backed news archive (`data/news-store/YYYY-MM.json`) works without Cloudflare.
- **Cloudflare D1 is optional and not active until a real account creates the database and binds `DB`.**
- **Historical price and freight-rate redistribution rights are not granted by the code.** The importer rejects unapproved manifests, but human verification of the provider's contract is still essential.
- Source prices, dividends and A/B signals are never invented when data is absent.

## Enable the Cloudflare D1 news archive (Windows PowerShell)

Requires [Node.js](https://nodejs.org/), [Wrangler](https://developers.cloudflare.com/workers/wrangler/install-and-update/), [GitHub CLI](https://cli.github.com/) and account access. Never paste a login token into Git or chat.

```powershell
npx wrangler login
gh auth login
npx wrangler d1 create stockwatch-research
# Copy the database_id UUID from the Wrangler response.
.\deploy\setup-cloudflare.ps1 -DatabaseId '<YOUR_REAL_DATABASE_UUID>'
```

The script creates a local `wrangler.toml` (ignored by Git), applies `database/0001_core.sql` to the **remote** database, deploys the Worker, asks you for its `/api/news/ingest` URL, and writes a newly generated secret to Cloudflare and GitHub without displaying it. A valid Cloudflare `DB` binding is required. Check the matching `/api/health` URL for `status:ok`.

Backfill archived news after it has run at least once:

```powershell
# In an environment with STOCKWATCH_ARCHIVE_URL and STOCKWATCH_ARCHIVE_TOKEN:
python scripts/push_archive.py --backfill
```

Or let the next market-hours GitHub scan upload the recent rolling window once the two secrets are configured. `--backfill` explicitly uploads all earlier Git-backed monthly partitions; the routine scan sends seven days. The endpoint deduplicates by article ID.

## Licensed A/B and shipping historical data

1. Obtain written public-redistribution rights from each relevant exchange/provider. **Public viewing, a chart embed or a free API key is not the same as redistribution permission.**
2. Have the licensed provider deliver date-keyed CSV rows (equity: `date,close,volume`; freight: `date,value`). Ensure all routes are correctly named and units stated (USD/day vs USD/tonne).
3. Record the provider, source URL, currency/adjustment policy and license reference in a JSON manifest. Check these against the actual contract.
4. Run `python scripts/import_licensed_history.py <csv> <manifest>` for each ticker or freight route. The frontend reads only licensed, dated local JSON and will show unavailable when it is absent.
5. Before interpreting A/B spread movements, confirm same trading days, same currency, share rights, costs, liquidity, corporate actions and whether the ratio has a stable distribution.

ICE/Baltic data is offered as a licensed product, including historical route data; contact the provider for appropriate publication rights: https://developer.ice.com/fixed-income-data-services/catalog/baltic-exchange .

## Validation

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
node --check worker/index.js
node --test tests/test_worker.mjs
node --check v4.js
node --check research.js
```

Before merging V4, run a real scanner scan, verify that all tracked companies appear even with missing quotes, check issuer matching and official source attribution, and confirm that `stocks.nordl.dev` is serving the deployed multi-page release. Do not describe D1 or licensed chart backfills as complete before their real external health/data checks pass.