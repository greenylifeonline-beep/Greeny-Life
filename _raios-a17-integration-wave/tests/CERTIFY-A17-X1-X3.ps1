# A17 X1–X3 certification. Must run in a clean child PowerShell process.
# Negative controls verify failure REASON, not merely command failure.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$wave = Split-Path -Parent $here

function Get-Python {
    foreach ($name in @('python3', 'python', 'py')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw 'PYTHON_NOT_FOUND'
}

$python = Get-Python
$child = @"
Set-Location -LiteralPath '$wave'
& '$python' '$here/certify_a17_x1_x3.py'
exit `$LASTEXITCODE
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
$proc = Start-Process -FilePath (Get-Command pwsh -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source) `
    -ArgumentList @('-NoProfile', '-EncodedCommand', $encoded) `
    -Wait -PassThru -NoNewWindow
if (-not $proc) {
    # Fallback: nested powershell.exe or direct python if pwsh missing.
    Write-Host 'PWSH_CHILD_UNAVAILABLE_FALLBACK_PYTHON'
    & $python (Join-Path $here 'certify_a17_x1_x3.py')
    exit $LASTEXITCODE
}
exit $proc.ExitCode
