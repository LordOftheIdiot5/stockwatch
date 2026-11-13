# Configure a single Stockwatch official-data key without exposing it in chat,
# Git history, PowerShell command history, or a permanent local file.
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('openfigi','entsoe','fred','eia')]
  [string]$Provider,
  [string]$Repository='LordOftheIdiot5/stockwatch'
)
$ErrorActionPreference='Stop'
$names=@{openfigi='STOCKWATCH_OPENFIGI_KEY';entsoe='STOCKWATCH_ENTSOE_TOKEN';fred='STOCKWATCH_FRED_API_KEY';eia='STOCKWATCH_EIA_API_KEY'}
$name=$names[$Provider]
if(-not (Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI is not installed.'}
$secure=Read-Host "Paste the $Provider API key or token (hidden input)" -AsSecureString
$ptr=[IntPtr]::Zero
$secret=$null
$file=Join-Path $env:TEMP ('stockwatch-source-'+[guid]::NewGuid().ToString('N')+'.env')
try {
  $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  $secret=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  if([string]::IsNullOrWhiteSpace($secret) -or $secret -match '[\r\n]'){
    throw 'Empty or invalid secret input.'
  }
  if($secret.Length -gt 1000){throw 'Secret exceeds expected size.'}
  if($secret -cmatch '[^\x20-\x7E]'){throw 'Secret contains unexpected non-ASCII characters.'}
  [IO.File]::WriteAllText($file, "$name=$secret" + [char]10, [Text.Encoding]::ASCII)
  & gh secret set --repo $Repository --env-file $file
  if($LASTEXITCODE -ne 0){throw 'GitHub CLI failed to set the secret.'}
} finally {
  if(Test-Path $file){Remove-Item -LiteralPath $file -Force}
  if($ptr -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
  $secret=$null
  $secure=$null
}
Write-Host "Configured GitHub Actions secret $name. No secret value printed."
Write-Host "Next: gh workflow run open-data.yml --repo $Repository --ref main"
