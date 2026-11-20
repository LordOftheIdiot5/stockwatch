# Euronext derived last-trade private archive — activation

## Status at 2026-11-21
On workflow run [44837283758](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44837283758), 15 Python tests passed, but the retention job failed with `EURONEXT_STAGE_FAILED ValueError`. GitHub reported `STOCKWATCH_R2_RETENTION_APPROVED: false` while the manual input requested `retain_private=true`. No archive readback or successful write was reported.

The request flag is **not** a legal rights approval. This workflow now checks approval before any ESMA baseline or Euronext report download and emits an actionable failure.

## To run validation without recording restricted data
```powershell
gh workflow run euronext-price-stage.yml --repo LordOftheIdiot5/stockwatch --ref main -f retain_private=false
```
The default run tests direct exchange retrieval and derives source-dated last eligible trade observations **in ephemeral process memory**, printing aggregate counts only. It does not store raw trades or prices, publish website prices, or claim a primary exchange close.

## Only after documented internal-retention approval
1. Review the specific Euronext source terms and scope, including whether *derived last trades* may be retained indefinitely in a private, nonpublic R2 bucket. Document the permission; free download alone is not commercial website publication or historical resale authorization.
2. A repository administrator may then set the existing GitHub Actions **repository variables** (not secrets) to `true`:
   - `STOCKWATCH_R2_RETENTION_APPROVED`
   - `STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED`
3. Verify scoped secrets are already configured for the private bucket `stockwatch-private-market-history`: `STOCKWATCH_R2_ACCOUNT_ID`, `STOCKWATCH_R2_ACCESS_KEY_ID`, `STOCKWATCH_R2_SECRET_ACCESS_KEY`. Do not share secrets or put them in commits.
4. Run:
```powershell
gh workflow run euronext-price-stage.yml --repo LordOftheIdiot5/stockwatch --ref main -f retain_private=true
```
5. **Acceptance gate:** the logs must show `EURONEXT_ARCHIVE_PREFLIGHT approved_private_r2`, `internalArchiveWritten=true`, `retainedPrivateDatedObservations` greater than zero, and `readbackVerified=true`. The job must finish **success**.

A private R2 archive is **not** a website display grant. Public price publication requires separate documented display rights, verified labelling as last eligible central-order-book trade (not official close), and UI tests. Commercial dataset redistribution requires further rights.

## What a failure means
- `STOCKWATCH_R2_RETENTION_APPROVED` false: general private source retention not approved; leave archiving disabled.
- `STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED` false: specific derived Euronext observation retention not approved; leave archiving disabled.
- Other `EURONEXT_STAGE_FAILED` errors: check source connectivity, authentication or scoped R2 write/readback. Never disable the approvals to work around failures or log raw quotes.
