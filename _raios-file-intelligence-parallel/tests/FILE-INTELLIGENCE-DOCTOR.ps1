$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pkg = Split-Path -Parent $here
$repo = Split-Path -Parent $pkg
$env:PYTHONPATH = Join-Path $pkg 'src'
Set-Location $repo
python3 -m raios_fi.doctor --report
if ($LASTEXITCODE -ne 0) {
    throw "FILE-INTELLIGENCE-DOCTOR failed with exit $LASTEXITCODE"
}
