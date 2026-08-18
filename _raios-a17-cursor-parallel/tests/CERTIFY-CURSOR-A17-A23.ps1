# Clean child PowerShell certification for A17.14–A23.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$wave = Split-Path -Parent $here
function Get-Python {
    foreach ($name in @('python3','python','py')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw 'PYTHON_NOT_FOUND'
}
$python = Get-Python
$child = @"
Set-Location -LiteralPath '$wave'
& '$python' '$here/certify_cursor_a17_a23.py'
exit `$LASTEXITCODE
"@
$pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
if ($pwsh) {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($child))
    $proc = Start-Process -FilePath $pwsh.Source -ArgumentList @('-NoProfile','-EncodedCommand',$encoded) -Wait -PassThru -NoNewWindow
    exit $proc.ExitCode
}
Write-Host 'PWSH_CHILD_UNAVAILABLE_FALLBACK_PYTHON'
& $python (Join-Path $here 'certify_cursor_a17_a23.py')
exit $LASTEXITCODE
