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

## EODData personal-use evaluation (NOT a public feed)

EODData's visible consumer plans are **personal-use only**. An API key, including one on a free account, does not grant public chart/quote redistribution. Do not commit a key, store it in client HTML or `v4.js`, or publish provider quotes to GitHub Pages/D1. A screenshot that exposes an API key should trigger regeneration/rotation in the EODData account.

There is an intentionally **offline-by-default**, single-request connectivity probe (`scripts/eoddata_private_probe.py`) using the provider's documented `GET /Exchange/List?apiKey=…`. It reads `EODDATA_API_KEY` from the local environment, displays only a sanitized connectivity result, and never stores or republishes data. It is **not** referenced by scanner workflows, the Worker, or public JavaScript. Example for Windows PowerShell (type secret only when prompted; process environment is cleared immediately afterward):

```powershell
$secret = Read-Host 'EODData API key (private local connectivity test)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
  $env:EODDATA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  python scripts/eoddata_private_probe.py --list-exchanges
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  Remove-Item Env:EODDATA_API_KEY -ErrorAction SilentlyContinue
  $secret.Dispose()
}
```

Before any commercial import, obtain a written license detailing website/public display rights, specific exchanges and data fields, historical retention, derived A/B ratios, and whether end users may export or download data. Validate symbol and exchange mappings and corporate-action adjustments. Then the existing `scripts/import_licensed_history.py` can import authorized daily prices with explicit source and rights manifests; **do not set `redistributionPermitted: true` on a personal/free plan.**

## A/B analytics and visuals

The A/B page renders a sourced one-year **statistical reference band** from the existing scanner's mean/standard deviation and the current A/B ratio. It is explicitly labeled **NOT a historical price chart**. When licensed same-day price bars for both share classes are present, a separate historical ratio chart supports 1M/3M/1Y/all controls. No synthetic historical chart or guessed sample points are generated.

## D1 ingestion repair — Windows PowerShell BOM

If a GitHub Scan job reports success while `/api/health` still shows `articles: 0`, inspect the `Optional database archive ingestion` step. A `UnicodeEncodeError` mentioning `\\ufeff` indicates an extra BOM in the GitHub secret.

With the existing `wrangler.toml` and authenticated `npx wrangler whoami` / `gh auth status`, **do not recreate the D1 database**. Rotate the Worker and GitHub ingest token together using a BOM-free ASCII input file:

```powershell
git fetch origin
git switch main
git pull --ff-only
.\\deploy\\repair-archive-secret.ps1 -ArchiveUrl "https://stockwatch-research-api.gauchovidar.workers.dev/api/news/ingest"
gh workflow run scan.yml --repo LordOftheIdiot5/stockwatch --ref main
```

The repair script generates a new 256-bit token, writes it only to short-lived temporary files, and passes it to both CLIs over raw standard input. No secret is printed, stored in Git, or published by the browser. Remove obsolete temporary files if the process is interrupted. The workflow now emits a warning if upload fails without blocking scanner data commits.

The Data health page independently checks the live D1 article count. An empty database is not equivalent to a healthy ingest pipeline; watch for a count greater than zero after the scan.


## Verify GitHub → Cloudflare authentication before rerunning the market scan

A successful market scan can still carry a D1 warning when the upload is marked optional.
The scan of 2026-11-13 00:51 UTC saved 147 news articles in the Git-backed
monthly archive but received **HTTP 403** from the D1 Worker.

Use the latest version of `deploy/repair-archive-secret.ps1`. It now writes
`STOCKWATCH_ARCHIVE_TOKEN` and `STOCKWATCH_ARCHIVE_URL` via a BOM-free
`gh secret set --env-file` file, rotates the matching Cloudflare secret,
and sends an authenticated empty-batch probe without storing any records.

```powershell
git switch main
git pull --ff-only origin main
.\deploy\repair-archive-secret.ps1 -ArchiveUrl "https://stockwatch-research-api.gauchovidar.workers.dev/api/news/ingest"
gh workflow run archive-d1-check.yml --repo LordOftheIdiot5/stockwatch --ref main
gh run list --repo LordOftheIdiot5/stockwatch --workflow archive-d1-check.yml --limit 1
```

Only after the authentication check succeeds should you dispatch a new
`scan.yml` run. The authentication smoke test uploads `{"items":[]}`
and never prints the secret. A 403 means the stored GitHub secret does not
match the Worker secret or an upstream rule is denying the request;
inspect the safe error category in the smoke-test log.
