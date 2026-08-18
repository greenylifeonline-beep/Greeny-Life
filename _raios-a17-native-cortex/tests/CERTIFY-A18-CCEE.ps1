#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$native = Split-Path -Parent $here
function Get-Python {
    foreach ($name in @('python3', 'python', 'py')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw 'PYTHON_NOT_FOUND'
}
$python = Get-Python
$env:PYTHONPATH = $native
& $python -m unittest discover -s (Join-Path $native 'tests') -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m ccee.doctor --report --root (Join-Path $native 'ccee/var/cert')
exit $LASTEXITCODE
