# Repair Stockwatch D1 ingestion authentication without exposing tokens.
# Run from the stockwatch-v4 repository root after Wrangler and GitHub login.
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^https://[^\s]+/api/news/ingest$')]
  [string]$ArchiveUrl,
  [ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')]
  [string]$Repository = 'LordOftheIdiot5/stockwatch'
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path '.\wrangler.toml')) { throw 'Run from the stockwatch repository with wrangler.toml configured.' }

# Windows PowerShell 5.1 and PowerShell 7 compatible 256-bit token.
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
$token = -join ($bytes | ForEach-Object { $_.ToString('x2') })

# PowerShell pipelines may add a UTF-8 BOM. Use raw ASCII stdin instead.
# Do not include the token in the command arguments, console output or Git.
$tokenPath = Join-Path $env:TEMP ('stockwatch-ingest-' + [guid]::NewGuid().ToString('N') + '.txt')
$urlPath = Join-Path $env:TEMP ('stockwatch-url-' + [guid]::NewGuid().ToString('N') + '.txt')
try {
  [IO.File]::WriteAllText($tokenPath, $token, [Text.Encoding]::ASCII)
  [IO.File]::WriteAllText($urlPath, $ArchiveUrl, [Text.Encoding]::ASCII)
  $worker = Start-Process -FilePath 'cmd.exe' -ArgumentList '/d /c npx wrangler secret put NEWS_INGEST_TOKEN --config wrangler.toml' -RedirectStandardInput $tokenPath -NoNewWindow -Wait -PassThru
  if ($worker.ExitCode -ne 0) { throw 'Cloudflare secret rotation failed.' }
  $github = Start-Process -FilePath 'cmd.exe' -ArgumentList "/d /c gh secret set STOCKWATCH_ARCHIVE_TOKEN --repo $Repository" -RedirectStandardInput $tokenPath -NoNewWindow -Wait -PassThru
  if ($github.ExitCode -ne 0) { throw 'GitHub token secret rotation failed.' }
  $url = Start-Process -FilePath 'cmd.exe' -ArgumentList "/d /c gh secret set STOCKWATCH_ARCHIVE_URL --repo $Repository" -RedirectStandardInput $urlPath -NoNewWindow -Wait -PassThru
  if ($url.ExitCode -ne 0) { throw 'GitHub URL secret update failed.' }
} finally {
  if (Test-Path $tokenPath) { Remove-Item -LiteralPath $tokenPath -Force }
  if (Test-Path $urlPath) { Remove-Item -LiteralPath $urlPath -Force }
  $token = $null
  [Array]::Clear($bytes, 0, $bytes.Length)
}
$health = Invoke-RestMethod -Uri $ArchiveUrl.Replace('/api/news/ingest', '/api/health') -Method Get
if ($health.status -ne 'ok') { throw 'Worker D1 health check did not pass.' }
Write-Host 'Cloudflare/GitHub secrets rotated with byte-exact ASCII input. Database is healthy.'
Write-Host 'Next: gh workflow run scan.yml --repo LordOftheIdiot5/stockwatch --ref main'
