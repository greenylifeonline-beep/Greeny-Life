# Lightning browser login. Skip if credentials.json already exists.
$ErrorActionPreference = "Stop"
$cred = Join-Path $env:USERPROFILE ".lightning\credentials.json"
if (Test-Path -LiteralPath $cred) {
    Write-Host "LIGHTNING_ALREADY_PRESENT $cred"
    Write-Host "Do not paste tokens in chat. If login is stale, delete that file then re-run this script."
    exit 0
}
if (-not (Get-Command lightning -ErrorAction SilentlyContinue)) {
    python -m pip install -U lightning-sdk
}
Write-Host "Browser will open. Sign in, wait until this window returns."
lightning login
Write-Host "LIGHTNING_LOGIN_EXIT=$LASTEXITCODE"
