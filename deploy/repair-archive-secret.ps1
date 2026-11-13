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
$envPath = Join-Path $env:TEMP ('stockwatch-github-' + [guid]::NewGuid().ToString('N') + '.env')
try {
  [IO.File]::WriteAllText($tokenPath, $token, [Text.Encoding]::ASCII)
  # GitHub CLI loads both secrets from a BOM-free ASCII dotenv file. This
  # avoids a separate PowerShell/native-command stdin conversion for GitHub.
  $dotenv = "STOCKWATCH_ARCHIVE_TOKEN=$token" + "`n" + "STOCKWATCH_ARCHIVE_URL=$ArchiveUrl" + "`n"
  [IO.File]::WriteAllText($envPath, $dotenv, [Text.Encoding]::ASCII)
  $worker = Start-Process -FilePath 'cmd.exe' -ArgumentList '/d /c npx wrangler secret put NEWS_INGEST_TOKEN --config wrangler.toml' -RedirectStandardInput $tokenPath -NoNewWindow -Wait -PassThru
  if ($worker.ExitCode -ne 0) { throw 'Cloudflare secret rotation failed.' }
  & gh secret set --repo $Repository --env-file $envPath
  if ($LASTEXITCODE -ne 0) { throw 'GitHub token/URL secret rotation failed.' }
  # Prove the Worker accepts this exact token without writing any article.
  # Wrangler can otherwise report success after receiving empty stdin.
  $probe = Invoke-RestMethod -Uri $ArchiveUrl -Method Post -ContentType 'application/json' -Body '{"items":[]}' -Headers @{ Authorization = "Bearer $token" }
  if ($probe.accepted -ne 0) { throw 'Worker ingestion authentication probe did not pass.' }
} finally {
  if (Test-Path $tokenPath) { Remove-Item -LiteralPath $tokenPath -Force }
  if (Test-Path $envPath) { Remove-Item -LiteralPath $envPath -Force }
  $token = $null
  [Array]::Clear($bytes, 0, $bytes.Length)
}
$health = Invoke-RestMethod -Uri $ArchiveUrl.Replace('/api/news/ingest', '/api/health') -Method Get
if ($health.status -ne 'ok') { throw 'Worker D1 health check did not pass.' }
Write-Host 'Cloudflare/GitHub secrets rotated with byte-exact ASCII input. Database is healthy.'
Write-Host 'Next: gh workflow run archive-d1-check.yml --repo LordOftheIdiot5/stockwatch --ref main'
