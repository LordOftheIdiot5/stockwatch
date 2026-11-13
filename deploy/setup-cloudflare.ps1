# Run from the Stockwatch repository root after logging into Cloudflare
# (npx wrangler login) and GitHub (gh auth login). Never commit credentials.
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')]
  [string]$DatabaseId,
  [string]$ArchiveUrl,
  [string]$Repository = 'LordOftheIdiot5/stockwatch'
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path 'wrangler.toml.example')) { throw 'Run from the Stockwatch repository root.' }
if (Test-Path 'wrangler.toml') { throw 'wrangler.toml exists. Inspect it rather than overwriting.' }
$tmpl = Get-Content 'wrangler.toml.example' -Raw
$tmpl.Replace('REPLACE_WITH_YOUR_D1_DATABASE_ID', $DatabaseId) | Set-Content 'wrangler.toml' -Encoding utf8
npx wrangler d1 execute stockwatch-research --remote --file=database/0001_core.sql
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
npx wrangler deploy --config wrangler.toml
if ($LASTEXITCODE -ne 0) { throw 'Worker deployment failed.' }
if (-not $ArchiveUrl) { $ArchiveUrl = Read-Host 'Paste the deployed HTTPS Worker URL ending in /api/news/ingest' }
if ($ArchiveUrl -notmatch '^https://[^\s]+/api/news/ingest$') { throw 'Invalid HTTPS ingestion URL.' }
# Route both secrets through BOM-free ASCII stdin; Windows PowerShell piping
# directly to native commands can prepend U+FEFF and break HTTP auth.
& .\\deploy\\repair-archive-secret.ps1 -ArchiveUrl $ArchiveUrl -Repository $Repository
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Secret configuration failed.' }
$health = Invoke-RestMethod -Uri $ArchiveUrl.Replace('/api/news/ingest','/api/health') -Method Get
if ($health.status -ne 'ok') { throw 'Worker health check did not return status=ok.' }
Write-Host 'Cloudflare D1 connected and Worker health check passed.'
Write-Host 'Backfill historical months using: python scripts/push_archive.py --backfill'
