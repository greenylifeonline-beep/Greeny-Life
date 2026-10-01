# Oracle browser session. NO VM. NO GPU. NO volume.
# Uses C:\o short-path install. Do NOT pip install oci-cli into Python312.
$ErrorActionPreference = "Stop"
$ociExe = "C:\o\Scripts\oci.exe"
if (-not (Test-Path -LiteralPath $ociExe)) {
    throw "Missing $ociExe. The working CLI is C:\o, not Python312 site-packages."
}
$env:Path = "C:\o\Scripts;C:\o;" + $env:Path
$env:PYTHONPATH = "C:\o\Lib\site-packages;" + [string]$env:PYTHONPATH
Write-Host "Using $ociExe"
Write-Host "Browser will open. Sign in to Oracle Cloud. When asked for region, pick yours (example: me-jeddah-1 or eu-frankfurt-1)."
Write-Host "Do not create a VM, GPU, bucket, or volume."
& $ociExe session authenticate
Write-Host "ORACLE_LOGIN_EXIT=$LASTEXITCODE"
